# Customizable PCR (CSV)

### Author
[Gabriel Straface (Ignea Lab @ McGill University)](https://www.mcgill.ca/)

## Categories
* PCR Protocols
  * Flexible PCR Setup

## Description
This protocol provides a fully customizable PCR workflow for the Opentrons Flex platform. It allows researchers to easily set up PCR reactions with flexible options for template DNA and primer addition. The protocol is designed to accommodate different experimental setups:

* Same template DNA/different primers
* Different template DNA/same primers
* Same template DNA/same primers
* Different template DNA/different primers

The protocol uses CSV input to specify well locations, allowing for custom plate layouts and efficient use of reagents. Users can specify which components (template DNA and/or primers) are the same across all samples, and the robot will add these automatically. Components that differ between samples can be added manually prior to the automated steps.

The protocol also includes options for standard PCR or colony PCR with a lysis step, giving researchers versatility for various applications. Thermocycling conditions can be completely customized through the protocol parameters, providing full control over denaturation, annealing, and extension settings.

---

### Modules
* [Thermocycler Module](https://shop.opentrons.com/products/thermocycler-module)

### Labware
* [Opentrons 96 Well PCR Plate Full Skirt](https://labware.opentrons.com/opentrons_96_wellplate_200ul_pcr_full_skirt)
* [Opentrons Flex 96 Tiprack 50µL](https://labware.opentrons.com/?category=tipRack)
* [Opentrons Flex 96 Tiprack 200µL](https://labware.opentrons.com/?category=tipRack)
* [NEST 12-Well Reservoir 15mL](https://labware.opentrons.com/nest_12_reservoir_15ml)

### Pipettes
* [Opentrons Flex 8-Channel 50µL Pipette](https://opentrons.com/products/flex-pipettes/)
* [Opentrons Flex 8-Channel 1000µL Pipette](https://opentrons.com/products/flex-pipettes/)

### Reagents
* PCR Master Mix (containing polymerase, buffer, dNTPs, etc.)
* Template DNA (genomic DNA, plasmid, etc.)
* PCR Primers (forward and reverse)

---

### Deck Setup
![deck layout](https://opentrons-protocol-library-website.s3.amazonaws.com/custom-README-images/pcr_flex_deck_layout.png)

* Slot C1: NEST 12-Well Reservoir
* Slot C2: PCR Plate
* Slot D1: 50µL Tiprack
* Slot D2: 200µL Tiprack
* Slots A1 & B1: Thermocycler Module
* Opentrons Flex Trash Chute
* Opentrons Flex Gripper

### Reagent Setup
* Reservoir (Slot C1):
  * Well A1: Master Mix
  * Well A2: Template DNA (when using the same template for all samples)
  * Well A3: Primers (when using the same primers for all samples)

---

### Protocol Steps
1. The protocol begins by parsing the CSV file to determine which wells require reagents.
2. Based on user parameters, the robot adds master mix to all specified PCR wells.
3. If the "Same Template DNA" option is enabled, the robot adds template DNA to all wells.
4. If the "Same Primers" option is enabled, the robot adds primers to all wells.
5. If any component needs to be added manually (different template DNA or different primers), the protocol pauses with instructions for manual addition.
6. The PCR plate is transferred to the thermocycler module.
7. If Colony PCR is enabled, a lysis step is performed at the specified temperature.
8. The thermocycler performs the initial denaturation step.
9. The specified number of PCR cycles are executed with the defined denaturation, annealing, and extension parameters.
10. A final extension step is performed.
11. The thermocycler cools to 4°C for sample preservation.
12. The thermocycler lid opens for sample retrieval.

### Process
1. Create a CSV file with your PCR well locations. The file should have three columns: Columns, Rows, and Wells. Example:
   ```
   Columns,Rows,Wells
   1,,
   ,A,
   ,,A2
   ,,B2
   ```
2. Specify your protocol parameters through the Opentrons App.
3. Download your protocol and unzip if needed.
4. Upload your protocol file (.py extension) to the [Opentrons App](https://opentrons.com/ot-app) in the `Protocol` tab.
5. Set up your deck according to the deck map, filling the reservoir with appropriate reagents.
6. Calibrate your labware, tiprack and pipette using the Opentrons App.
7. If using manual additions, prepare your template DNA and/or primer samples.
8. Hit 'Run'.
9. When prompted (if applicable), add different template DNA or primers to the appropriate wells.

### Additional Notes
* The protocol is optimized for smart tip usage, minimizing the number of tips required by grouping adjacent wells.
* For colony PCR, ensure colonies are properly suspended in the PCR plate wells before starting the protocol.
* If using the same template DNA or primers for all wells, make sure to provide adequate volume in the reservoir (Well A2 or A3, respectively).
* The protocol can be run in debug mode for testing and verification without performing actual liquid handling.

If you have any questions about this protocol, please contact the Protocol Development Team by filling out the [Troubleshooting Survey](https://protocol-troubleshooting.paperform.co/).
