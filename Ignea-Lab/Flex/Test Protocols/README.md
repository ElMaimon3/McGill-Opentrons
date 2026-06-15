# Flex Test Protocols

These scripts were used to develop and calibrate the miniprep protocols in [`Ignea-Lab/Flex/`](..) (`flex_miniprep_zymo.py` and `flex_miniprep_omega.py`). They are **not** intended for routine lab use, but are kept here as references for re-calibrating depths/timings if labware, reagents, or chemistry changes.

| Script | Purpose |
|---|---|
| [validation-protocol.py](validation-protocol.py) | Transfers liquid out of a reservoir well in small steps while adjusting pipetting depth via the `vol_to_height` formula, to confirm the formula tracks the liquid level correctly as the well empties. |
| [miniprep_depth_validation.py](miniprep_depth_validation.py) | Moves a pipette to user-specified depths in the sample plate and the magnetic-module collection plate, to check/calibrate aspiration depths used by the miniprep protocols. |
| [miniprep_time_validation.py](miniprep_time_validation.py) | Runs the first steps of the miniprep (lysis buffer addition and heater-shaker incubation) to measure real timings for those steps. |
| [flex_miniprep_zymo_SHORT.py](flex_miniprep_zymo_SHORT.py) | Abbreviated version of `flex_miniprep_zymo.py` that starts partway through the protocol (assumes lysis/neutralization already done), for faster end-to-end testing of the wash/elution steps. |

If you change reagent chemistry, labware, or plate types, re-run the relevant validation script before trusting the height/timing constants in the main miniprep protocols.
