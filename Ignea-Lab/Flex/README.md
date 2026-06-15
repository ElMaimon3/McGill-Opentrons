# Ignea Lab — Opentrons Flex Protocols

Protocols in this folder target the **Opentrons Flex** (`apiLevel: 2.21`). Most use the 8-channel pipettes, the Flex waste chute, and one or more of the Heater-Shaker, Temperature, Thermocycler, and Magnetic Block modules.

## PCR protocols

| Protocol | Description |
|---|---|
| [Flex_PCR_CSV.py](Flex_PCR_CSV.py) | Fully customizable PCR/colony PCR. A CSV file specifies which wells need samples; the robot adds master mix (and template DNA/primers, depending on parameters) automatically. Full documentation: [Flex_PCR_CSV.md](Flex_PCR_CSV.md). |
| [Flex_PCR_Columns.py](Flex_PCR_Columns.py) | For plates where template DNA is already pipetted by hand into specific columns. The robot adds master mix (and optionally primers) to each selected column, then runs the thermocycler. |
| [PCR_HALF.py](PCR_HALF.py) | For plates that have been pipetted entirely by hand. The robot only runs the thermocycler program. |
| [Flex_PCR_CSV_deprecated.py](Flex_PCR_CSV_deprecated.py) | Earlier version of the CSV-based PCR protocol, kept for reference. Use `Flex_PCR_CSV.py` instead. |

## Miniprep protocols

| Protocol | Description |
|---|---|
| [flex_miniprep_zymo.py](flex_miniprep_zymo.py) | Pellet-free magnetic-bead miniprep using Zymo Research Zyppy chemistry (v1.3). Samples are specified via CSV; uses the Heater-Shaker and Temperature modules with the 8-channel pipettes. |
| [flex_miniprep_omega.py](flex_miniprep_omega.py) | Pellet-free magnetic-bead miniprep using Omega Bio-tek chemistry, 8-channel pipettes. |

## Utilities

| File | Description |
|---|---|
| [eppendorf_for_flex.py](eppendorf_for_flex.py) | Moves a pipette tip to a user-specified depth inside a 1.5 mL Eppendorf tube. Used to visually calibrate the depth formulas (`vol_to_height`) used by the protocols above. |

## Test Protocols

The [`Test Protocols/`](<Test Protocols>) subfolder contains development and calibration scripts used while tuning the miniprep protocols. They are not intended for routine lab use — see [Test Protocols/README.md](<Test Protocols/README.md>).

## Running a protocol

1. Upload the desired `.py` file to the [Opentrons App](https://opentrons.com/ot-app).
2. Configure the runtime parameters exposed in `add_parameters` (volumes, sample counts, thermocycler settings, CSV well list, `debug` mode, etc.).
3. Set up the deck according to the protocol's comments/deck setup, calibrate labware and pipettes, then run.
4. If a `debug` parameter is available, run a debug pass first — debug mode simulates pipette movement without dispensing reagents, which is useful for checking deck layout and timing before committing real samples/reagents.
