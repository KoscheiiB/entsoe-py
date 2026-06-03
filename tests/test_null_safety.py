"""Offline regression tests for null-safe XML parsing.

These cover ENTSO-E responses that omit optional elements:
  - generation-per-plant timeseries with no <name>
  - installed-capacity-per-plant timeseries with no <psrtype>
  - empty installed-capacity responses (no <TimeSeries> at all)

Before the null-safety fix each of these raised AttributeError/KeyError.
No network or API key required.
"""
import pandas as pd

from entsoe.parsers import (
    _parse_generation_timeseries,
    parse_installed_capacity_per_plant,
)
from entsoe.series_parsers import _extract_timeseries


def _first_timeseries(xml_text):
    return next(_extract_timeseries(xml_text))


GENERATION_NO_NAME = """
<GL_MarketDocument>
  <TimeSeries>
    <mRID>42</mRID>
    <MktPSRType><psrType>B02</psrType></MktPSRType>
    <curveType>A01</curveType>
    <Period>
      <timeInterval><start>2024-01-01T00:00Z</start><end>2024-01-01T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>100</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""

INSTALLED_NO_PSRTYPE = """
<GL_MarketDocument>
  <TimeSeries>
    <registeredResource.mRID>PLANT1</registeredResource.mRID>
    <registeredResource.name>Plant One</registeredResource.name>
    <inBiddingZone_Domain.mRID>10YBZ</inBiddingZone_Domain.mRID>
    <production_PowerSystemResources.highVoltageLimit>220</production_PowerSystemResources.highVoltageLimit>
    <Period>
      <timeInterval.start>2024-01-01T00:00Z</timeInterval.start>
      <Point><quantity>100</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""


def test_generation_per_plant_missing_name_falls_back_to_mrid():
    soup = _first_timeseries(GENERATION_NO_NAME)
    series = _parse_generation_timeseries(soup, per_plant=True)
    # Series name is a tuple ending in the plant identifier; with <name> absent
    # it must fall back to the mRID ("42") instead of raising AttributeError.
    assert "42" in series.name


def test_installed_capacity_missing_psrtype_does_not_raise():
    df = parse_installed_capacity_per_plant(INSTALLED_NO_PSRTYPE)
    assert "Production Type" in df.columns
    # psrtype was absent -> value is null, not an exception.
    assert pd.isna(df.loc["PLANT1", "Production Type"])
    assert df.loc["PLANT1", "Name"] == "Plant One"


def test_installed_capacity_empty_response_returns_empty_frame():
    df = parse_installed_capacity_per_plant("")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
