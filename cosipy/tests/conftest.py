"""Provides shared fixtures and methods for tests.

Use these to replace duplicated code.

For generating objects within a test function's scope, call a fixture
directly:

    .. code-block:: python
        
        def test_foobar(self, conftest_mock_grid):
            grid_object = conftest_mock_grid
            grid_object.set_foo(foo=bar)
            ...
"""

from unittest.mock import patch

import matplotlib.pyplot as plt
import numba
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from cosipy.cpkernel.grid import Grid


# Function patches
@pytest.fixture(scope="function", autouse=False)
def conftest_mock_check_file_exists():
    """Override checks when mocking files."""

    patcher = patch("os.path.exists")
    mock_exists = patcher.start()
    mock_exists.return_value = True


@pytest.fixture(scope="function", autouse=False)
def conftest_mock_open_dataset(conftest_mock_xr_dataset):
    """Override xr.open_dataset with mock dataset."""

    patcher = patch("xarray.open_dataset")
    mock_exists = patcher.start()
    dataset = conftest_mock_xr_dataset.copy(deep=True)
    mock_exists.return_value = dataset


@pytest.fixture(scope="function", autouse=False)
def conftest_hide_plot():
    """Suppress plt.show(). Does not close plots."""

    patcher = patch("matplotlib.pyplot.show")
    mock_exists = patcher.start()
    mock_exists.return_value = True


@pytest.fixture(name="conftest_rng_seed", scope="function", autouse=False)
def fixture_conftest_rng_seed() -> np.random.Generator:
    """Sets seed for random number generator to 444.

    Returns:
        Random number generator with seed=444.
    """

    random_generator = np.random.default_rng(seed=444)
    rng_state = random_generator.__getstate__()["state"]["state"]
    assert rng_state == 201734421534842192264806664122757988751

    yield random_generator


# Mock GRID data
@pytest.fixture(
    name="conftest_mock_grid_values", scope="function", autouse=False
)
def fixture_conftest_mock_grid_values() -> dict:
    """Constructs the layer values used to generate Grid objects.

    Returns:
        Numba arrays for layers' heights, snowpack densities,
        temperatures, and liquid water content.
    """

    layer_values = {}
    layer_values["layer_heights"] = numba.float64([0.1, 0.2, 0.3, 0.5, 0.5])
    layer_values["layer_densities"] = numba.float64([250, 250, 250, 917, 917])
    layer_values["layer_temperatures"] = numba.float64(
        [260, 270, 271, 271.5, 272]
    )
    layer_values["layer_liquid_water_content"] = numba.float64(
        [0.0, 0.0, 0.0, 0.0, 0.0]
    )

    assert isinstance(layer_values, dict)
    for array in layer_values.values():
        assert isinstance(array, np.ndarray)
        assert len(array) == 5

    yield layer_values


@pytest.fixture(name="conftest_mock_grid", scope="function", autouse=False)
def fixture_conftest_mock_grid(conftest_mock_grid_values: dict) -> Grid:
    """Constructs a Grid object.

    .. note:: Use with caution, as this fixture assumes Grid objects are
        correctly instantiated.

    Returns:
        Grid object with numba arrays for the layers' heights,
        densities, temperatures, and liquid water content.
    """

    data = conftest_mock_grid_values.copy()
    grid_object = Grid(
        layer_heights=data["layer_heights"],
        layer_densities=data["layer_densities"],
        layer_temperatures=data["layer_temperatures"],
        layer_liquid_water_content=data["layer_liquid_water_content"],
    )
    assert isinstance(grid_object, Grid)

    yield grid_object


@pytest.fixture(name="conftest_mock_grid_ice", scope="function", autouse=False)
def fixture_conftest_mock_grid_ice(conftest_mock_grid_values: dict) -> Grid:
    """Constructs a Grid object for ice layers.

    .. note:: Use with caution, as this fixture assumes Grid objects are
        correctly instantiated.

    Returns:
        Grid object for ice layers with numba arrays for layer heights,
        layer densities, layer temperatures, and layer liquid water
        content.
    """

    data = conftest_mock_grid_values.copy()
    grid_object = Grid(
        layer_heights=data["layer_heights"][3:4],
        layer_densities=data["layer_densities"][3:4],
        layer_temperatures=data["layer_temperatures"][3:4],
        layer_liquid_water_content=data["layer_liquid_water_content"][3:4],
    )
    assert isinstance(grid_object, Grid)

    yield grid_object


# Mock xarray Dataset
@pytest.fixture(
    name="conftest_mock_xr_dataset_dims", scope="function", autouse=False
)
def fixture_conftest_mock_xr_dataset_dims() -> dict:
    """Yields dimensions for constructing an xr.Dataset."""

    dimensions = {}
    reference_time = pd.Timestamp("2009-01-01T12:00:00")
    dimensions["time"] = pd.date_range(reference_time, periods=4, freq="6H")
    dimensions["latitude"] = [30.460, 30.463, 30.469, 30.472]
    dimensions["longitude"] = [90.621, 90.624, 90.627, 90.630, 90.633]
    dimensions["name"] = ["time", "lat", "lon"]

    yield dimensions


@pytest.fixture(
    name="conftest_mock_xr_dataset", scope="function", autouse=False
)
def fixture_conftest_mock_xr_dataset(
    conftest_mock_xr_dataset_dims: dict, conftest_rng_seed: np.random.Generator
) -> xr.Dataset:
    """Constructs mock xarray Dataset of output .nc file.

    Returns:
        Dataset with data for elevation and surface data. The data is of
        shape ()
    """

    _ = conftest_rng_seed
    dims = conftest_mock_xr_dataset_dims.copy()
    lengths = [
        len(dims["time"]),
        len(dims["latitude"]),
        len(dims["longitude"]),
    ]
    elevation = xr.Variable(
        data=1000 + 10 * np.random.rand(lengths[1], lengths[2]),
        dims=dims["name"][1:],
        attrs={"long_name": "Elevation", "units": "m"},
    )
    temperature = xr.Variable(
        data=15 + 8 * np.random.randn(lengths[0], lengths[1], lengths[2]),
        dims=dims["name"],
        attrs={"long_name": "Surface temperature", "units": "K"},
    )

    dataset = xr.Dataset(
        data_vars=dict(HGT=elevation, TS=temperature),
        coords=dict(
            time=dims["time"],
            lat=(["lat"], dims["latitude"]),
            lon=(["lon"], dims["longitude"]),
            reference_time=dims["time"][0],
        ),
        attrs=dict(description="Weather related data."),
    )
    assert isinstance(dataset, xr.Dataset)

    for key, length in zip(dims["name"], lengths):
        assert dataset[key].shape == (length,)

    assert "time" not in dataset.HGT.dims
    assert dataset.HGT.shape == (lengths[1], lengths[2])
    assert dataset.HGT.long_name == "Elevation"
    for key in ["TS"]:  # in case we add more variables
        assert "time" in dataset[key].dims
        assert dataset[key].shape == (lengths[0], lengths[1], lengths[2])
        assert dataset[key][0].shape == (lengths[1], lengths[2])

    yield dataset


class TestBoilerplate:
    """Provides boilerplate methods for serialising tests.

    The class is instantiated via the `conftest_boilerplate` fixture.
    The fixture is autoused, and can be called directly within a test::

    ..code-block:: python

        def test_foo(self, conftest_boilerplate)"

            foobar = [...]
            conftest_boilerplate.bar(foobar)

    Methods are arranged with their appropriate test::

    .. code-block:: python

        def foo(self, ...):
            pass

        def test_foo(self ...):
            pass
    """

    def check_plot(self, plot_params: dict, title: str = ""):
        """Check properties of figure/axis pairs."""

        assert "plot" in plot_params
        assert isinstance(plot_params["plot"][0], plt.Figure)
        assert isinstance(plot_params["plot"][1], plt.Axes)
        compare_ax = plot_params["plot"][1]
        if "title" in plot_params:
            compare_title = f"{plot_params['title']}{title}"
            assert compare_ax.get_title("center") == compare_title
        if "x_label" in plot_params:
            assert compare_ax.xaxis.get_label_text() == plot_params["x_label"]
        if "y_label" in plot_params:
            assert compare_ax.yaxis.get_label_text() == plot_params["y_label"]

    def test_check_plot(self):
        """Validate tests for plot attributes."""

        test_title = ", Inner Scope"
        plt.close("all")
        figure_strings = plt.figure()
        axis_strings = plt.gca()
        plt.title(f"Test Title{test_title}")
        plt.xlabel("Test x-label")
        plt.ylabel("Test y-label")

        figure_none = plt.figure()
        axis_none = plt.gca()

        test_params = {
            "strings": {
                "plot": (figure_strings, axis_strings),
                "title": "Test Title",
                "x_label": "Test x-label",
                "y_label": "Test y-label",
            },
            "none": {"plot": (figure_none, axis_none)},
        }

        for test_pair in test_params.values():
            self.check_plot(plot_params=test_pair, title=test_title)
        plt.close("all")

    def set_timestamp(self, day: bool) -> str:
        """Returns timestamp string for a day or for a timestep."""

        if day:
            timestamp = "2009-01-01"
        else:
            timestamp = "2009-01-01T12:00:00"

        return timestamp

    def test_set_timestamp(self):
        for arg_day in [True, False]:
            compare_time = self.set_timestamp(day=arg_day)
            assert isinstance(compare_time, str)
            if arg_day:
                assert compare_time == "2009-01-01"
            else:
                assert compare_time == "2009-01-01T12:00:00"

    def set_rng_seed(self, seed=444):
        """Sets seed for random number generator to 444.

        Returns:
            Random number generator with seed=444.
        """

        random_generator = np.random.default_rng(seed=seed)

        return random_generator

    def test_set_rng_seed(self):
        rng_none = self.set_rng_seed()
        assert isinstance(rng_none, np.random.Generator)
        rng_none_state = rng_none.__getstate__()["state"]["state"]
        rng_123 = self.set_rng_seed(seed=123)
        assert isinstance(rng_123, np.random.Generator)
        rng_123_state = rng_123.__getstate__()["state"]["state"]
        rng_444 = self.set_rng_seed(seed=444)
        assert isinstance(rng_444, np.random.Generator)
        rng_444_state = rng_444.__getstate__()["state"]["state"]

        assert all(
            isinstance(state, int)
            for state in [rng_none_state, rng_123_state, rng_444_state]
        )
        assert rng_none_state == rng_444_state
        assert not rng_444_state == rng_123_state

    def regenerate_grid_values(
        self, grid: Grid, key: str, distribution: str
    ) -> Grid:
        rng = self.set_rng_seed()
        if distribution == "random":
            for idx in range(0, grid.number_nodes - 1):
                grid.set_node_liquid_water_content(
                    idx, rng.uniform(low=0.01, high=0.05)
                )
        elif distribution == "static":
            for idx in range(0, grid.number_nodes - 1):
                grid.set_node_liquid_water_content(idx, 1.0)
        elif distribution == "decreasing":
            for idx in range(0, grid.number_nodes - 1):
                grid.set_node_liquid_water_content(
                    idx, 0.01 * grid.number_nodes
                )
        else:
            for idx in range(0, grid.number_nodes - 1):
                grid.set_node_liquid_water_content(idx, 0)

        return grid

    def test_generate_grid_values(self):
        grid = self.regenerate_grid_values(distribution="static")
        assert isinstance(grid, Grid)

    def test_boilerplate_integration(self):
        """Integration test for boilerplate methods."""

        self.test_check_plot()
        self.test_set_timestamp()
        self.test_set_rng_seed()


@pytest.fixture(name="conftest_boilerplate", scope="function", autouse=False)
def conftest_boilerplate():
    """Yields class containing methods for common tests."""

    test_boilerplate = TestBoilerplate()
    test_boilerplate.test_boilerplate_integration()

    yield TestBoilerplate()