import numpy as np
import pytest

import constants
from cosipy.cpkernel.node import Node


class TestNodeGetter:
    """Tests get methods for Node objects.

    Attributes:
        height (float): Layer height [:math:`m`]
        snow_density (float): Snow density [:math:`kg~m^{-3}`]
        temperature (int): Layer temperature [:math:`K`]
        lwc (float): Liquid water content [:math:`m~w.e.`]
        ice_fraction (float): Volumetric ice fraction [-]
    """

    height = 0.1
    snow_density = 200.0
    temperature = 270.0
    lwc = 0.2
    ice_fraction = 0.4

    def test_node_init(self, conftest_boilerplate):
        """Inherit methods from parent."""

        test_node = Node(
            height=self.height,
            snow_density=self.snow_density,
            temperature=self.temperature,
            liquid_water_content=self.lwc,
            ice_fraction=self.ice_fraction,
        )
        assert test_node
        assert isinstance(test_node, Node)

        conftest_boilerplate.check_output(
            variable=test_node.temperature,
            x_type=float,
            x_value=self.temperature,
        )
        conftest_boilerplate.check_output(test_node.height, float, self.height)
        conftest_boilerplate.check_output(
            test_node.liquid_water_content, float, self.lwc
        )
        conftest_boilerplate.check_output(
            test_node.refreeze, float, 0.0
        )
        # conftest_boilerplate.check_output(
        #     test_node.snow_density, float, self.snow_density
        # )

    def create_node(
        self,
        height: float = height,
        snow_density: float = snow_density,
        temperature: float = temperature,
        lwc: float = lwc,
        ice_fraction: float = ice_fraction,
    ) -> Node:
        """Instantiate a Node."""

        node = Node(
            height=height,
            snow_density=snow_density,
            temperature=temperature,
            liquid_water_content=lwc,
            ice_fraction=ice_fraction,
        )
        assert isinstance(node, Node)

        return node

    def test_create_node(self):
        node = self.create_node()
        assert isinstance(node, Node)

    def calculate_irreducible_water_content(
        self, current_ice_fraction: float
    ) -> float:
        """Calculate irreducible water content."""
        if current_ice_fraction <= 0.23:
            theta_e = 0.0264 + 0.0099 * (
                (1 - current_ice_fraction) / current_ice_fraction
            )
        elif (current_ice_fraction > 0.23) & (current_ice_fraction <= 0.812):
            theta_e = 0.08 - 0.1023 * (current_ice_fraction - 0.03)
        else:
            theta_e = 0.0

        return theta_e

    @pytest.mark.parametrize("arg_ice_fraction", [0.2, 0.5, 0.9])
    def test_calculate_irreducible_water_content(self, arg_ice_fraction):
        theta_e = self.calculate_irreducible_water_content(arg_ice_fraction)
        assert isinstance(theta_e, float)

    def test_node_getter_functions(self):
        node = self.create_node()
        assert np.isclose(node.get_layer_height(), self.height)
        assert np.isclose(node.get_layer_temperature(), self.temperature)
        assert np.isclose(node.get_layer_ice_fraction(), self.ice_fraction)
        assert np.isclose(node.get_layer_liquid_water_content(), self.lwc)
        assert np.isclose(node.get_layer_refreeze(), 0.0)

    def test_node_get_layer_height(self, conftest_boilerplate):
        node = self.create_node()
        assert conftest_boilerplate.check_output(
            node.get_layer_height(), float, self.height
        )

    def test_node_get_layer_temperature(self, conftest_boilerplate):
        node = self.create_node()
        assert conftest_boilerplate.check_output(
            node.get_layer_temperature(), float, self.temperature
        )

    def test_node_get_layer_liquid_water_content(self, conftest_boilerplate):
        node = self.create_node()
        assert conftest_boilerplate.check_output(
            node.get_layer_liquid_water_content(), float, self.lwc
        )

    def test_node_get_layer_refreeze(self, conftest_boilerplate):
        node = self.create_node()
        assert conftest_boilerplate.check_output(
            node.get_layer_refreeze(), float, 0.0
        )

    @pytest.mark.parametrize("arg_ice_fraction", [0.0, 0.1, 0.9, None])
    def test_node_get_layer_ice_fraction(
        self, conftest_boilerplate, arg_ice_fraction
    ):
        node = self.create_node(ice_fraction=arg_ice_fraction)
        if arg_ice_fraction is None:
            test_ice_fraction = (
                self.snow_density
                - (1 - (self.snow_density / constants.ice_density))
                * constants.air_density
            ) / constants.ice_density
        else:
            test_ice_fraction = arg_ice_fraction
        compare_ice_fraction = node.get_layer_ice_fraction()
        conftest_boilerplate.check_output(
            compare_ice_fraction, float, test_ice_fraction
        )
        assert np.isclose(compare_ice_fraction, node.ice_fraction)

    def test_node_get_layer_air_porosity(self, conftest_boilerplate):
        node = self.create_node()
        test_porosity = 1 - self.lwc - self.ice_fraction
        conftest_boilerplate.check_output(
            node.get_layer_air_porosity(), float, test_porosity
        )

    def test_node_get_layer_density(self, conftest_boilerplate):
        node = self.create_node()
        test_density = (
            self.ice_fraction * constants.ice_density
            + self.lwc * constants.water_density
            + node.get_layer_air_porosity() * constants.air_density
        )
        assert conftest_boilerplate.check_output(
            node.get_layer_density(), float, test_density
        )

    def test_node_get_layer_porosity(self, conftest_boilerplate):
        node = self.create_node()
        test_porosity = 1 - self.lwc - self.ice_fraction
        conftest_boilerplate.check_output(
            node.get_layer_porosity(), float, test_porosity
        )

    def test_node_get_layer_specific_heat(self, conftest_boilerplate):
        node = self.create_node()
        test_specific_heat = (
            (1 - self.lwc - self.ice_fraction) * constants.spec_heat_air
            + self.ice_fraction * constants.spec_heat_ice
            + self.lwc * constants.spec_heat_water
        )
        conftest_boilerplate.check_output(
            node.get_layer_specific_heat(), float, test_specific_heat
        )

    def test_node_get_layer_cold_content(self, conftest_boilerplate):
        node = self.create_node()
        test_cold_content = (
            -node.get_layer_specific_heat()
            * node.get_layer_density()
            * self.height
            * (self.temperature - constants.zero_temperature)
        )
        conftest_boilerplate.check_output(
            node.get_layer_cold_content(), float, test_cold_content
        )

    def test_node_get_layer_thermal_conductivity(self, conftest_boilerplate):
        node = self.create_node()
        test_thermal_conductivity = (
            self.ice_fraction * constants.k_i
            + node.get_layer_porosity() * constants.k_a
            + self.lwc * constants.k_w
        )
        conftest_boilerplate.check_output(
            node.get_layer_thermal_conductivity(),
            float,
            test_thermal_conductivity,
        )

    def test_node_get_layer_thermal_diffusivity(self, conftest_boilerplate):
        node = self.create_node()
        test_thermal_diffusivity = node.get_layer_thermal_conductivity() / (
            node.get_layer_density() * node.get_layer_specific_heat()
        )
        conftest_boilerplate.check_output(
            node.get_layer_thermal_diffusivity(),
            float,
            test_thermal_diffusivity,
        )

    @pytest.mark.parametrize("arg_ice_fraction", [0.1, 0.9])
    def test_node_get_layer_irreducible_water_content(
        self, conftest_boilerplate, arg_ice_fraction
    ):
        node = self.create_node(ice_fraction=arg_ice_fraction)

        test_irreducible_water_content = (
            self.calculate_irreducible_water_content(
                node.get_layer_ice_fraction()
            )
        )
        conftest_boilerplate.check_output(
            node.get_layer_irreducible_water_content(),
            float,
            test_irreducible_water_content,
        )
