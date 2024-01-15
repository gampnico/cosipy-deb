import numpy as np
from numba import njit

import constants
from config import use_debris


@njit(cache=False)
def updateAlbedo(GRID, surface_temperature, albedo_snow) -> float:
    """Update the surface albedo.

    Args:
        GRID (Grid): Glacier mesh.

    Returns:
        Updated surface albedo.
    """

    albedo_allowed = ["Oerlemans98", "Bougamont05", "Lejeune13"]
    if (use_debris) or (constants.albedo_method == "Lejeune13"):
        alphaMod = method_lejeune(GRID)  # snow-covered debris
    elif constants.albedo_method == "Oerlemans98":
        alphaMod = method_Oerlemans(GRID)
    elif constants.albedo_method == "Bougamont05":
        alphaMod, albedo_snow = method_Bougamont(GRID, surface_temperature, albedo_snow)

    else:
        error_message = (
            f'Albedo method = "{constants.albedo_method}"',
            f"is not allowed, must be one of",
            f'{", ".join(albedo_allowed)}',
        )
        raise ValueError(" ".join(error_message))

    return alphaMod, albedo_snow


@njit(cache=False)
def get_surface_properties(GRID) -> tuple:
    """Get snowpack properties.

    Args:
        GRID (Grid): Glacier mesh.

    Returns:
        tuple[float, float, float]: Height and timestamp of fresh snow,
        and the hours elapsed since the last snowfall.
    """

    # Get hours since the last snowfall
    # First get fresh snow properties (height and timestamp)
    fresh_snow_height, fresh_snow_timestamp, _ = GRID.get_fresh_snow_props()

    # Get time difference between last snowfall and now
    hours_since_snowfall = (fresh_snow_timestamp) / 3600.0

    # If fresh snow disappears faster than the snow ageing scale then
    # set the hours_since_snowfall to the old values of the underlying
    # snowpack
    if (hours_since_snowfall < (constants.albedo_mod_snow_aging * 24)) & (
        fresh_snow_height <= 0.0
    ):
        GRID.set_fresh_snow_props_to_old_props()
        (
            fresh_snow_height,
            fresh_snow_timestamp,
            _,
        ) = GRID.get_fresh_snow_props()

        # Update time difference between last snowfall and now
        hours_since_snowfall = (fresh_snow_timestamp) / 3600.0

    return fresh_snow_height, fresh_snow_timestamp, hours_since_snowfall


@njit(cache=False)
def get_simple_albedo(elapsed_time: float) -> float:
    """Get surface albedo neglecting snowpack depth.

    From Oerlemans & Knap (1998).

    Args:
        elapsed_time: Hours elapsed since last snowfall.

    Returns:
        Surface albedo without accounting for snowpack depth.
    """

    albedo = constants.albedo_firn + (
        constants.albedo_fresh_snow - constants.albedo_firn
    ) * np.exp((-elapsed_time) / (constants.albedo_mod_snow_aging * 24.0))

    return albedo


@njit(cache=False)
def method_Oerlemans(GRID) -> float:
    """Get surface albedo using method from Oerlemans & Knap (1998).

    Args:
        GRID (Grid): Glacier mesh.

    Returns:
        Surface albedo.
    """
    _, _, hours_since_snowfall = get_surface_properties(GRID)

    # Check if snow or ice
    if GRID.get_node_density(0) <= constants.snow_ice_threshold:
        # Get current snowheight from layer height
        h = GRID.get_total_snowheight()  # np.sum(GRID.get_height()[0:idx])

        # Surface albedo according to Oerlemans & Knap (1998), JGR
        alphaSnow = get_simple_albedo(elapsed_time=hours_since_snowfall)
        alphaMod = alphaSnow + (constants.albedo_ice - alphaSnow) * np.exp(
            (-1.0 * h) / (constants.albedo_mod_snow_depth / 100.0)
        )

    else:
        # If no snow cover than set albedo to ice albedo
        alphaMod = constants.albedo_ice

    return alphaMod

@njit(cache=False)
def method_Bougamont(GRID, surface_temperature, albedo_snow):
    # Get hours since the last snowfall
    # First get fresh snow properties (height and timestamp)
    _, fresh_snow_timestamp, _ = GRID.get_fresh_snow_props()

    # Get time difference between last snowfall and now:
    hours_since_snowfall = (fresh_snow_timestamp) / 3600.0

    # Convert integration time from seconds to days:
    dt_days = constants.dt / 86400.0

    # Note: accounting for disapearance of uppermost fresh snow layer difficult due to non-constant decay rate. Unsure how to implement.

    # Get current snowheight from layer height:
    h = GRID.get_total_snowheight()

    # Check if snow or ice:
    if GRID.get_node_density(0) <= constants.snow_ice_threshold:
        if surface_temperature >= constants.zero_temperature:
            # Snow albedo decay timescale (t*) on a melting snow surface:
            t_star = constants.t_star_wet
        else:
            # Snow albedo decay timescale (t*) on a dry snow surface:
            if surface_temperature < constants.t_star_cutoff:
                t_star = (
                    constants.t_star_dry
                    + (constants.zero_temperature - constants.t_star_cutoff)
                    * constants.t_star_K
                )
            else:
                t_star = (
                    constants.t_star_dry
                    + (constants.zero_temperature - surface_temperature)
                    * constants.t_star_K
                )

        # Effect of snow albedo decay due to the temporal metamorphosis of snow (Bougamont et al. 2005 - based off Oerlemans & Knap 1998):
        # Exponential function discretised in order to account for variable surface temperature-dependant decay timescales.
        albedo_snow = (
            albedo_snow - (albedo_snow - constants.albedo_firn) / t_star * dt_days
        )

        # Reset if snowfall in current timestep
        if hours_since_snowfall == 0:
            albedo_snow = constants.albedo_fresh_snow

        # Effect of surface albedo decay due to the snow depth (Oerlemans & Knap 1998):
        alphaMod = albedo_snow + (constants.albedo_ice - albedo_snow) * np.exp(
            (-1.0 * h) / (constants.albedo_mod_snow_depth / 100.0)
        )

    else:
        # If no snow cover than set albedo to ice albedo
        alphaMod = constants.albedo_ice

    # Ensure output value is of the float data type.
    alphaMod = float(alphaMod)

    return alphaMod, albedo_snow

@njit(cache=False)
def get_albedo_weight_lejeune(snow_depth: float) -> float:
    """Weighting for snow-covered debris albedo (Lejeune et al., 2007).

    Args:
        snow_depth: Height of snowpack above debris.

    Returns:
        Albedo weighting.
    """

    albedo_weight = min(
        1.0,
        (snow_depth / constants.critical_snowpack_thickness)
        ** constants.lejeune_weighting_coefficient,
    )

    return albedo_weight


@njit(cache=False)
def method_lejeune(GRID) -> float:
    """Get snow-covered debris albedo (Lejeune et al., 2007).

    Args:
        GRID (Grid): Glacier mesh.

    Returns:
        Albedo for snow-covered debris.
    """

    if GRID.get_node_ntype(0) == 0:
        fresh_snow_height, _, hours_since_snowfall = get_surface_properties(
            GRID=GRID
        )

        albedo_weight = get_albedo_weight_lejeune(snow_depth=fresh_snow_height)
        albedo_snow = get_simple_albedo(elapsed_time=hours_since_snowfall)
        albedo = (
            albedo_weight * albedo_snow
            + (1 - albedo_weight) * constants.albedo_debris
        )
    else:  # no need to calculate weights
        albedo = constants.albedo_debris

    return albedo


### idea; albedo decay like (Brock et al. 2000)? or?
### Schmidt et al 2017 >doi:10.5194/tc-2017-67, 2017 use the same albedo parameterisation from Oerlemans and Knap 1998 with a slight updated implementation of considering the surface temperature?
