# McGill iGEM

Starter templates for McGill iGEM team protocols on the **Opentrons OT-2** (`apiLevel: 2.19`).

| File | Description |
|---|---|
| [sample.py](sample.py) | Blank protocol template. Already has the `metadata`/`requirements` boilerplate, an example runtime parameter (`some_number`), and a `debug` toggle with `if/else` branches wired up — fill in `metadata`, labware/pipette setup, and the protocol steps in `run()`. |

## Creating a new protocol

1. Copy `sample.py` to a new file named after your protocol.
2. Fill in `metadata` (`protocolName`, `author`, `description`).
3. Add/adjust runtime parameters in `add_parameters` for any values a user should be able to change from the Opentrons App (volumes, sample counts, etc.).
4. Implement the deck/labware/pipette setup and protocol steps in `run()`. Keep the `debug` branch as a simulation path (e.g. `move_to`/`delay`/`comment` instead of `aspirate`/`dispense`) so the protocol can be dry-run without consuming reagents.
5. Upload the finished `.py` file to the [Opentrons App](https://opentrons.com/ot-app) to test.
