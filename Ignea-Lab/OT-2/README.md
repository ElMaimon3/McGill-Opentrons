# Ignea Lab — Opentrons OT-2 Protocols

Protocols in this folder target the **Opentrons OT-2** (`apiLevel: 2.19`).

## PCR protocols

| Protocol | Description |
|---|---|
| [PCR.py](PCR.py) | Fully customizable PCR/colony PCR. Sample well locations are entered directly in the script; master mix and primers are added automatically. Full documentation: [PCR.md](PCR.md). |
| [BIEN585_PCR1.py](BIEN585_PCR1.py) | PCR protocol pre-configured for the BIEN 585 course (colony PCR, 95°C/600s initial denaturation, 30 cycles). Sample locations are read from a CSV. |
| [BIEN585_PCR2.py](BIEN585_PCR2.py) | Same as above with a different thermocycler program (98°C/180s initial denaturation, 35 cycles, longer extension). |

## Miniprep protocols

| Protocol | Description |
|---|---|
| [miniprepV_2.1_single.py](miniprepV_2.1_single.py) | Pellet-free magnetic-bead miniprep using a single-channel pipette (up to 11 samples in wells D1–F4). Lysis, neutralization, magnetic binding, multi-step washes, drying, and elution. |
| [miniprepV_2.1_multi.py](miniprepV_2.1_multi.py) | Same workflow as above, adapted for a multi-channel pipette and deep-well plates (samples in columns 6–9). |
| [miniprep_full.py](miniprep_full.py) | Single-channel miniprep with configurable aspiration depths and wash-buffer levels, plus built-in debug modes for depth calibration and magnetic-module testing. |

## Cloning / other workflows

| Protocol | Description |
|---|---|
| [alginate_bead_prep.py](alginate_bead_prep.py) | Produces alginate beads by dispensing droplets from a multi-channel pipette into a gelling bath, adjusting the source-well aspiration height as it empties. |
| [gibsonassembly.py](gibsonassembly.py) | Sets up a Gibson Assembly reaction (linearized vector + 2 fragments + water + master mix) on the temperature module and incubates at 50°C. |
| [restriction_digestion.py](restriction_digestion.py) | Sets up a restriction digest (plasmid + insert + CutSmart buffer + water + two enzymes) on the temperature module and incubates at 37°C. |
| [plasmid_ligation.py](plasmid_ligation.py) | Gel extraction + ligation protocol. **Work in progress** — not yet implemented. |

## Debug / test

| File | Description |
|---|---|
| [multi_channel_debug.py](multi_channel_debug.py) | Small 2-sample test of the multi-channel miniprep's lysis/mixing step. |

## Running a protocol

1. Check the `add_parameters` function near the top of the file — protocols that define one (e.g. `PCR.py`, `alginate_bead_prep.py`, `miniprep_full.py`) expose volumes, sample counts, and other options as runtime parameters configurable from the Opentrons App. Protocols without `add_parameters` (e.g. the miniprep V2.1 scripts, `gibsonassembly.py`, `restriction_digestion.py`) are configured by editing the hardcoded well locations/volumes near the top of `run()` directly in the script before uploading.
2. Upload the `.py` file to the [Opentrons App](https://opentrons.com/ot-app).
3. Set up the deck with labware and reagents as described in the protocol's comments, calibrate, and run.
