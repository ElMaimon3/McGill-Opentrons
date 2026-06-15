# McGill-Opentrons

Opentrons **OT-2** and **Flex** liquid-handling protocols written and maintained for research labs and student teams at McGill University. Each protocol is a self-contained Python file written against the [Opentrons Protocol API](https://docs.opentrons.com/v2/) and is meant to be uploaded directly to the [Opentrons App](https://opentrons.com/ot-app).

## Repository structure

```
McGill-Opentrons/
├── Ignea-Lab/              Protocols for the Ignea Lab
│   ├── Flex/               Opentrons Flex protocols
│   │   └── Test Protocols/ Validation / calibration scripts (not for routine lab use)
│   └── OT-2/                Opentrons OT-2 protocols
└── McGill-iGEM/            Protocol templates for the McGill iGEM team
```

Each folder above has its own README with a full breakdown of the protocols it contains:

* [`Ignea-Lab/Flex/`](Ignea-Lab/Flex/README.md) — Flex protocols (PCR, miniprep)
* [`Ignea-Lab/Flex/Test Protocols/`](<Ignea-Lab/Flex/Test Protocols/README.md>) — calibration / validation scripts
* [`Ignea-Lab/OT-2/`](Ignea-Lab/OT-2/README.md) — OT-2 protocols (PCR, miniprep, cloning)
* [`McGill-iGEM/`](McGill-iGEM/README.md) — starter template for new protocols

## Protocol overview

### Opentrons Flex ([Ignea-Lab/Flex](Ignea-Lab/Flex))

| Protocol | Purpose | Status |
|---|---|---|
| [Flex_PCR_CSV.py](Ignea-Lab/Flex/Flex_PCR_CSV.py) | Fully customizable PCR / colony PCR. Reads a CSV to decide which wells get master mix, template DNA and primers added automatically | ✅ Active — see [docs](Ignea-Lab/Flex/Flex_PCR_CSV.md) |
| [Flex_PCR_Columns.py](Ignea-Lab/Flex/Flex_PCR_Columns.py) | PCR for plates where template DNA is already loaded; robot adds master mix (and optionally primers) column by column | ✅ Active |
| [PCR_HALF.py](Ignea-Lab/Flex/PCR_HALF.py) | Thermocycler-only run for plates that have been pipetted by hand | ✅ Active |
| [flex_miniprep_zymo.py](Ignea-Lab/Flex/flex_miniprep_zymo.py) | Pellet-free magnetic-bead miniprep using Zymo Zyppy chemistry (8-channel, heater-shaker + temperature module) | ✅ Active (v1.3) |
| [flex_miniprep_omega.py](Ignea-Lab/Flex/flex_miniprep_omega.py) | Pellet-free magnetic-bead miniprep using Omega chemistry (8-channel) | ✅ Active |
| [eppendorf_for_flex.py](Ignea-Lab/Flex/eppendorf_for_flex.py) | Moves a pipette to a user-specified depth inside a 1.5 mL tube — used to calibrate aspiration heights | 🔧 Utility |
| [Flex_PCR_CSV_deprecated.py](Ignea-Lab/Flex/Flex_PCR_CSV_deprecated.py) | Earlier version of the CSV-based PCR protocol | ⚠️ Deprecated — kept for reference |

### Flex Test Protocols ([Ignea-Lab/Flex/Test Protocols](<Ignea-Lab/Flex/Test Protocols>))

Development/validation scripts used to tune the miniprep protocols above (depth calibration, timing measurements, shortened run-throughs). Not intended for routine lab work — see the folder [README](<Ignea-Lab/Flex/Test Protocols/README.md>) for details.

### Opentrons OT-2 ([Ignea-Lab/OT-2](Ignea-Lab/OT-2))

| Protocol | Purpose | Status |
|---|---|---|
| [PCR.py](Ignea-Lab/OT-2/PCR.py) | Fully customizable PCR / colony PCR with manual sample-location entry | ✅ Active — see [docs](Ignea-Lab/OT-2/PCR.md) |
| [BIEN585_PCR1.py](Ignea-Lab/OT-2/BIEN585_PCR1.py) / [BIEN585_PCR2.py](Ignea-Lab/OT-2/BIEN585_PCR2.py) | PCR protocols pre-configured for the BIEN 585 course | ✅ Active |
| [miniprepV_2.1_single.py](Ignea-Lab/OT-2/miniprepV_2.1_single.py) | Pellet-free magnetic-bead miniprep, single-channel pipette (up to 11 samples) | ✅ Active |
| [miniprepV_2.1_multi.py](Ignea-Lab/OT-2/miniprepV_2.1_multi.py) | Pellet-free magnetic-bead miniprep, multi-channel pipette | ✅ Active |
| [miniprep_full.py](Ignea-Lab/OT-2/miniprep_full.py) | Single-channel miniprep with configurable aspiration depths and built-in debug/calibration modes | ✅ Active |
| [alginate_bead_prep.py](Ignea-Lab/OT-2/alginate_bead_prep.py) | Produces alginate beads by dispensing droplets into a gelling bath, tracking source-well height as it empties | ✅ Active |
| [gibsonassembly.py](Ignea-Lab/OT-2/gibsonassembly.py) | Sets up a Gibson Assembly reaction (vector + fragments + master mix) and incubates on the temperature module | ✅ Active |
| [restriction_digestion.py](Ignea-Lab/OT-2/restriction_digestion.py) | Sets up a restriction digest (plasmid + insert + enzymes + buffer) and incubates on the temperature module | ✅ Active |
| [multi_channel_debug.py](Ignea-Lab/OT-2/multi_channel_debug.py) | Small 2-sample test of the multi-channel miniprep's lysis step | 🔧 Debug/test |
| [plasmid_ligation.py](Ignea-Lab/OT-2/plasmid_ligation.py) | Gel extraction + ligation protocol | 🚧 Work in progress |

### McGill iGEM ([McGill-iGEM](McGill-iGEM))

| File | Purpose | Status |
|---|---|---|
| [sample.py](McGill-iGEM/sample.py) | Blank starter template (metadata, requirements and a `debug` parameter already wired up) for new iGEM protocols | 📄 Template |

## Status legend

| Symbol | Meaning |
|---|---|
| ✅ Active | Up to date and used in the lab |
| ⚠️ Deprecated | Superseded by a newer protocol, kept for reference only |
| 🔧 Utility / Debug | Calibration or development helper, not a full protocol |
| 🚧 Work in progress | Incomplete |
| 📄 Template | Starting point for a new protocol |

## Using these protocols

1. Open the protocol file you need and review the **Runtime Parameters** section near the top (`add_parameters`) — most protocols expose volumes, sample counts, thermocycler settings, and a `debug`/simulation mode as configurable options.
2. Upload the `.py` file to the [Opentrons App](https://opentrons.com/ot-app) under the **Protocols** tab.
3. Set the runtime parameters for your run from the App.
4. Set up the deck and load labware/reagents as described in the protocol's deck/reagent setup (see the per-folder docs linked above for diagrams where available).
5. Calibrate labware, tip racks, and pipettes.
6. If the protocol has a `debug` parameter, consider running it in debug mode first to dry-run pipette movements without consuming reagents.
7. Run the protocol, following any on-screen pause/comment prompts for manual steps.

## Requirements

* **OT-2 protocols** target Opentrons Protocol API `2.19`.
* **Flex protocols** target Opentrons Protocol API `2.21` and require a Flex robot (some use the Heater-Shaker, Temperature, Thermocycler, and Magnetic Block modules, plus the Flex waste chute/gripper).

## Questions / troubleshooting

For Opentrons-specific issues (calibration, labware definitions, App errors), see the [Opentrons support documentation](https://support.opentrons.com/) or the [Troubleshooting Survey](https://protocol-troubleshooting.paperform.co/). For questions about a specific protocol, check the protocol's `metadata['author']` field or the relevant folder README.
