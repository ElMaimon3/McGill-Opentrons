# Opentrons Protocol for Minipreps with Magbeads (OT-2)
from opentrons import protocol_api

metadata = {
    'protocolName': 'Minipreps with Magbeads (OT-2, Single Channel)',
    "author": "Gabriel Straface, Dan Voicu (Ignea Lab @ McGill University)",
    'description': '''Opentrons protocol for minipreps with magbeads (OT-2). Requires pellet from 2mL of culture. Consult miniprep.md for more details.
    DO NOT FORGET TO TURN ON THE HEPA FAN ON MAX''',
    'apiLevel': '2.19'
}

# Runtime Parameters (Recommended)
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_float(
        variable_name = "eppendorf_depth",
        display_name = "Eppendorf Depth",
        description = "",
        default = 36.5,
        minimum = 1.0,
        maximum = 60.0,
        unit = "mm"
    )
    parameters.add_float(
        variable_name = "well_depth",
        display_name = "Deep Well Depth",
        description = "",
        default = 41.5,
        minimum = 1.0,
        maximum = 60.0,
        unit = "mm"
    )
    parameters.add_float(
        variable_name = "wb1_level",
        display_name = "Wash Buffer 1 level",
        description = "",
        default = 15.0,
        minimum = 3.4,
        maximum = 15.0,
        unit = "mL"
    )
    parameters.add_float(
        variable_name = "wb2_level",
        display_name = "Wash Buffer 2 level",
        description = "",
        default = 15.0,
        minimum = 3.4,
        maximum = 15.0,
        unit = "mL"
    )
    parameters.add_bool(
        variable_name = "debug",
        display_name = "Debugging Mode",
        description = "Place an empty eppendorf in A1 of the tube holder, make sure A1 of the deep plate is empty",
        default = False
    )
    parameters.add_str(
        variable_name="debug_protocol",
        display_name="Debug Protocol",
        description="To change the part that is being tested", 
        choices=[
            {"display_name": "Tube and deep well depth", "value": "depth"},
            {"display_name": "Mag module test", "value": "mag_mod"},
            {"display_name": "Both", "value":"both"}
        ],
        default="depth"
    )

# Protocol function
def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap','3')
    heater_shaker_module = protocol.load_module('heaterShakerModuleV1', '1')
    hs_adapter = heater_shaker_module.load_adapter("opentrons_96_deep_well_adapter")
    hs_plate = hs_adapter.load_labware('nest_96_wellplate_2ml_deep')
    tube_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '6')
    mag_module = protocol.load_module('magnetic module gen2', '10')
    mag_plate = mag_module.load_labware('nest_96_wellplate_2ml_deep')

    # Define sample locations on each of the 96-well plates (eg. 'A1','A2'):
    hs_samples = [well.top(-protocol.params.well_depth) for well in hs_plate.wells('G1', 'G2')]
    mag_samples = [well.top(-protocol.params.well_depth) for well in mag_plate.wells('G1', 'G2')]

    # Define reagent locations
    resuspension_solution = small_tube_rack.wells_by_name()['A1'].top(-protocol.params.eppendorf_depth)
    lysis_solution = small_tube_rack.wells_by_name()['A2'].top(-protocol.params.eppendorf_depth)
    neutralization_solution = small_tube_rack.wells_by_name()['A3'].top(-protocol.params.eppendorf_depth)
    isopropanol = small_tube_rack.wells_by_name()['A4'].top(-protocol.params.eppendorf_depth)
    magbeads = small_tube_rack.wells_by_name()['B1'].top(-protocol.params.eppendorf_depth)
    wash_buffer_1 = tube_rack.wells_by_name()['A1']
    wash_buffer_2 = tube_rack.wells_by_name()['A2']
    waste = tube_rack.wells_by_name()['A3'].top(-1)
    elution_buffer = small_tube_rack.wells_by_name()['B2'].top(-protocol.params.eppendorf_depth)
    sample_wells = [small_tube_rack.wells_by_name()[well_name].top(-protocol.params.eppendorf_depth) for well_name in ['D5', 'D6']]
    sample_wells_elu = [small_tube_rack.wells_by_name()[well_name].top(1-protocol.params.eppendorf_depth) for well_name in ['D5', 'D6']]
    final_samples = [small_tube_rack.wells_by_name()[well_name] for well_name in ['D1', 'D2']]
    num_samples = len(sample_wells)

    # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5')])
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', '8')])
    wb1 = protocol.params.wb1_level -1 #If purple tubes
    wb2 = protocol.params.wb2_level -1
    if not protocol.params.debug:
        # Perform miniprep protocol part 1

        # Step 1: Resuspend pelleted bacterial cells in 200 µL of Resuspension Solution
        p300.transfer(200, resuspension_solution, sample_wells, mix_after=(6, 200), new_tip='always')

        # Step 2: Add 200 µL of Lysis Solution and mix gently 4-6 times
        p300.transfer(200, lysis_solution, sample_wells, mix_before=(2, 300), mix_after=(3, 300), new_tip='always')

        # Incubate for 2 min at room temperature, offset to include pipetting time
        protocol.delay(seconds=100)

        # Step 3: Add 200 µL of Neutralization Solution and mix immediately and gently 4-6 times
        p300.transfer(200, neutralization_solution, sample_wells, mix_after=(4, 300), new_tip='always')

        # Step 4: Add 50 µL of isopropanol and mix immediately and gently 4-6 times
        p300.transfer(50, isopropanol, sample_wells, mix_after=(4, 300), new_tip='always')

        protocol.pause("Spin the sample tubes at 1600 x g for 5m, place them back in the rack and resume.")
        # Part 2
        # Engage the heater-shaker latch
        heater_shaker_module.close_labware_latch()

        # Add magbeads to the deep plate on the heater-shaker
        p20.pick_up_tip()
        p20.mix(3,20,magbeads)
        p20.blow_out(magbeads)
        p20.drop_tip()
        p300.transfer(25, magbeads, hs_samples)

        # Add isopropanol and mix
        p300.transfer(250, isopropanol, hs_samples, mix_after=(3, 200))

        # Add supernatant from the cell lysate and mix gently
        for i in range(num_samples):
            p300.pick_up_tip()
            p300.transfer(300, sample_wells_elu[i] , hs_samples[i] , new_tip='never')
            p300.transfer(300, sample_wells_elu[i] , hs_samples[i] , new_tip='never')
            p300.transfer(50, sample_wells_elu[i] , hs_samples[i] , mix_after=(4, 250) , new_tip='never')
            p300.drop_tip()

        # Incubate for 5 minutes in the heater-shaker at 80°C, 900 rpm
        heater_shaker_module.set_target_temperature(81)
        heater_shaker_module.set_and_wait_for_shake_speed(900)
        heater_shaker_module.wait_for_temperature()
        protocol.delay(minutes=5)
        heater_shaker_module.deactivate_shaker()
        heater_shaker_module.deactivate_heater()
        # Disengage the heater-shaker latch and manually move the deep plate to the magnetic module
        heater_shaker_module.open_labware_latch()
        protocol.pause('Please move the deep plate from the heater-shaker to the magnetic module and resume.')

        # Engage the magnetic module for 3 minutes and remove all the liquid
        mag_module.engage(height_from_base=5)
        protocol.delay(minutes=3)
        for well in mag_samples:
            p300.pick_up_tip()
            p300.transfer(300, well, waste, new_tip='never')
            p300.transfer(300, well, waste, new_tip='never')
            p300.transfer(50, well, waste, new_tip='never')
            p300.drop_tip()
        # WASH STEP 1
        for j in range(2):
            # Disengage the magnetic module and add wash buffer 1, mixing 3 times
            mag_module.disengage()
            for well in mag_samples:
                p300.pick_up_tip()
                p300.transfer(300, wash_buffer_1.top(-vol_to_height(wb1)), well, new_tip='never')
                wb1 -= 0.3
                p300.transfer(200, wash_buffer_1.top(-vol_to_height(wb1)), well, new_tip='never')       
                wb1 -= 0.3
                p300.transfer(200, wash_buffer_1.top(-vol_to_height(wb1)), well, new_tip='never', mix_after=(4,250))
                wb1 -= 0.2
                p300.drop_tip()

            # Engage the magnetic module for 3 minutes and remove all the liquid
            mag_module.engage(height_from_base=5)
            protocol.delay(minutes=3)
            for well in mag_samples:
                p300.pick_up_tip()
                p300.transfer(300, well, waste, new_tip='never')
                p300.transfer(200, well, waste, new_tip='never')
                p300.transfer(200, well, waste, new_tip='never')
                p300.drop_tip()
        # WASH STEP 2
        for j in range(2):
            # Disengage the magnetic module and add wash buffer 2, mixing 3 times
            mag_module.disengage()
            for well in mag_samples:
                p300.pick_up_tip()
                p300.transfer(300, wash_buffer_2.top(-vol_to_height(wb2)), well, new_tip='never')
                wb2 -= 0.3
                p300.transfer(200, wash_buffer_2.top(-vol_to_height(wb2)), well, new_tip='never')
                wb2 -= 0.3       
                p300.transfer(200, wash_buffer_2.top(-vol_to_height(wb2)), well, new_tip='never', mix_after=(4,250))
                wb2 -= 0.2
                p300.drop_tip()

            # Engage the magnetic module for 3 minutes and remove all the liquid
            mag_module.engage(height_from_base=5)
            protocol.delay(minutes=3)
            for well in mag_samples:
                p300.pick_up_tip()
                p300.transfer(300, well, waste, new_tip='never')
                p300.transfer(200, well, waste, new_tip='never')
                p300.transfer(200, well, waste, new_tip='never')
                p300.drop_tip()
        mag_module.disengage()

        # Delay the protocol to manually move the deep plate back to the heater-shaker
        protocol.pause('Please move the deep plate back to the heater-shaker and resume.')

        # Engage the heater-shaker latch
        heater_shaker_module.close_labware_latch()

        # Incubate with no shaking at 40°C for 2 minutes to dry
        heater_shaker_module.set_and_wait_for_temperature(40)
        protocol.delay(minutes=2)

        # Add elution buffer and mix
        p300.transfer(100, elution_buffer, hs_samples, mix_after=(2, 50), new_tip='always')

        # Incubate for 5 minutes at 60°C, 900rpm
        heater_shaker_module.set_target_temperature(61)
        heater_shaker_module.set_and_wait_for_shake_speed(900)
        heater_shaker_module.wait_for_temperature()
        protocol.delay(minutes=5)
        heater_shaker_module.deactivate_shaker()
        heater_shaker_module.deactivate_heater()

        # Disengage the heater-shaker latch and manually move the deep plate back to the magnetic module
        heater_shaker_module.open_labware_latch()
        protocol.pause('Please move the deep plate back to the magnetic module and resume.')

        # Engage the magnetic module for 2 minutes and collect the eluent
        mag_module.engage(height_from_base=5)
        protocol.delay(minutes=3)

        for j in range(2):
            p300.transfer(100, mag_samples[j], final_samples[j])

        # The plasmid DNA is now in the tube on the tube rack and can be stored at -20
    else:
        if protocol.params.debug_protocol == "depth":
            heater_shaker_module.close_labware_latch()
            p300.pick_up_tip()
            p300.move_to(resuspension_solution)
            protocol.pause('Validate Eppendorf Depth')
            p300.move_to(hs_plate.wells_by_name()['A1'].top(-protocol.params.well_depth))
            protocol.pause("Validate well depth")
            p300.drop_tip()
            heater_shaker_module.open_labware_latch()
            protocol.pause("Move plate to mag module")
            p300.pick_up_tip()
            p300.move_to(mag_plate.wells_by_name()['A1'].top(-protocol.params.well_depth))
            protocol.pause("Validate well depth")
            p300.drop_tip()
        elif protocol.params.debug_protocol == "mag_mod":
            protocol.pause("Place deep plate in mag module, have magbeads and ethanol available")
            p300.pick_up_tip()
            p300.mix(3,50,magbeads)
            p300.transfer(25,magbeads,mag_samples,new_tip='never')
            p300.transfer(300,isopropanol,mag_samples,new_tip='never')
            for s in mag_samples:
                p300.mix(3,300,s)
            p300.drop_tip()
            mag_module.engage(height_from_base=5)
            protocol.delay(minutes=2)
            mag_module.disengage()
        elif protocol.params.debug_protocol == "both":
            heater_shaker_module.close_labware_latch()
            p300.pick_up_tip()
            p300.move_to(resuspension_solution)
            protocol.pause('Validate Eppendorf Depth')
            p300.move_to(hs_plate.wells_by_name()['A1'].top(-protocol.params.well_depth))
            protocol.pause("Validate well depth")
            p300.drop_tip()
            heater_shaker_module.open_labware_latch()
            protocol.pause("Move plate to mag module")
            p300.pick_up_tip()
            p300.move_to(mag_plate.wells_by_name()['A1'].top(-protocol.params.well_depth))
            protocol.pause("Validate well depth")
            p300.drop_tip()
            protocol.pause("Place deep plate in mag module, have magbeads and ethanol available")
            p300.pick_up_tip()
            p300.mix(3,50,magbeads)
            p300.transfer(25,magbeads,mag_samples,new_tip='never')
            p300.transfer(300,isopropanol,mag_samples,new_tip='never')
            for s in mag_samples:
                p300.mix(3,300,s)
            p300.drop_tip()
            mag_module.engage(height_from_base=5)
            protocol.delay(minutes=2)
            mag_module.disengage()

def vol_to_height(vol):
    if vol < 2:
        raise ValueError('One of the buffers or washes is too low! Please add more')
    return round(-7.39231*vol + 121.885) #111 for the red tubes