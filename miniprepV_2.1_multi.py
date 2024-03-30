# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (OT-2)
from opentrons import protocol_api

metadata = {
    'protocolName': 'Pellet-Free Minipreps with Magbeads (OT-2, Multi Channel)',
    'author': 'Your Name',
    'description': '''Opentrons protocol for pellet-free minipreps with magbeads (OT-2). Requires XuL of culture, XuL of concentrated lysis buffer, 
    XuL of concentrated neutralization buffer, XuL of magbeads, XuL of wash per sample. DO NOT FORGET TO TURN ON THE HEPA FAN ON MAX''',
    'apiLevel': '2.15'
}
# THIS PROTOCOL HAS NOT BEEN IMPLEMENTED YET, IT IS A COPY OF THE SINGLE CHANNEL PROTOCOL
# Protocol function
def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap','9')
    plate_96 = protocol.load_labware('nest_96_wellplate_2ml_deep', '1')
    tube_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '2')
    reagent_reservoir = protocol.load_labware('nest_12_reservoir_15ml', '3')
    mag_module = protocol.load_module('magnetic module gen2', '4')
    mag_plate = mag_module.load_labware('nest_96_wellplate_2ml_deep')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', '6')
    # SETTINGS MUST BE ADJUSTED FOR EACH RUN
    # Define available reagents (mL):
    available_lysis = 15.0
    available_neutralization = 15.0
    available_binding = 15.0
    available_PB = 15.0
    available_PE = 15.0
    available_ethanol = 15.0
    # Define sample locations on each of the 96-well plates. This represents columns (eg. 'A1' is the first,'A2' is the second):
    # First multi channel run notes: one row is non resuspended, the other is, can remove tips from tiprack to preserve tips and reagents for unused rows
    initial_samples = plate_96.wells('A6','A7')
    mag_samples = mag_plate.wells('A6','A7')
    elute_samples = elute_plate.wells('A6','A7')
    mag_samples_s = mag_plate.wells('A6','B6','A7','B7')
    # Define reagent locations
    lysis_buffer = reagent_reservoir['A1']
    neutralization_buffer = reagent_reservoir['A2']
    binding_buffer = reagent_reservoir['A3']
    PB = reagent_reservoir['A4']
    magbeads = small_tube_rack['A1']
    PE = reagent_reservoir['A5']
    ethanol = reagent_reservoir['A6']
    P = small_tube_rack['A3']
    N = small_tube_rack['A4']
    waste = reagent_reservoir['A12']
    elution_buffer = reagent_reservoir['A7']
    # DEBUG SETTINGS
    # Define samples with special properties:
    regular_samples = plate_96.wells('A6')
    conc_samples = plate_96.wells('A7')
    # Define wash settings:
    # Two_wash = mag_plate.wells('D1','D2','D3','E1','F1')
    # PB_wash = mag_plate.wells('E2','F2')
    # PE_wash = mag_plate.wells('E3','F3')
    Eth_wash = mag_plate.wells('A5','A6')
    depth = 39 # Depth to take supernatant from deep plate
    magbead_incubation_time  = 5 # Total, minutes
    sample_volume = 940
    lysis_buffer_amount = 470
    neutralization_buffer_amount = 239
    binding_buffer_amount = 301


    # Load pipettes
    p300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5'),protocol.load_labware('opentrons_96_tiprack_300ul', '11'),protocol.load_labware('opentrons_96_tiprack_300ul', '10')])
    p300_1 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '8')])

    num_samples = len(initial_samples)
    if len(mag_samples) != len(initial_samples) or len(initial_samples) != len(elute_samples):
        raise ValueError("The amount of samples in each plate are not the same!")

    # Perform miniprep protocol

    # Add lysis buffer to samples
    for sample in regular_samples:
        p300_1.pick_up_tip()
        p300_1.transfer(250, P.top(-37), sample, new_tip='never')
        p300_1.drop_tip()
    
    for sample in conc_samples:
        p300.pick_up_tip()
        for i in range(lysis_buffer_amount//300):
            p300.transfer(300, lysis_buffer.top(-depth), sample, new_tip='never')
            p300.mix(1, 300, sample.top(-depth))
        p300.transfer(lysis_buffer_amount%300,lysis_buffer.top(-depth), sample, new_tip='never')
        p300.blow_out(sample)
        p300.drop_tip()
    sample_volume += lysis_buffer_amount

    # Offset code might not be ideal, need improvment
    # Calculate time offset x
    num_steps = len(regular_samples)
    time_offset = 60*num_steps
    if time_offset<300:
        protocol.delay(seconds=(300-time_offset))

    for sample in regular_samples:
        p300_1.pick_up_tip()
        p300_1.transfer(250, N.top(-37), sample, new_tip='never')
        p300_1.mix(1, 300, sample)
        p300_1.drop_tip()

    for sample in conc_samples:
        p300.pick_up_tip()
        p300.transfer(neutralization_buffer_amount, neutralization_buffer.top(-depth), sample, new_tip='never')
        p300.mix(2, 300, sample)
        p300.blow_out(sample)
        p300.drop_tip()
    sample_volume += neutralization_buffer_amount

    # Incubate 10 minutes
    protocol.delay(minutes=10)

    # Add magnetic beads to the plate on the mag module
    p300_1.pick_up_tip()
    for sample in mag_samples_s:
        p300_1.flow_rate.aspirate=50
        p300_1.mix(3,50,magbeads.top(-37))
        p300_1.transfer(40, magbeads.top(-37), sample, new_tip='never')
        p300_1.blow_out(sample)
    p300_1.drop_tip()
    
    # Take bacterial samples and put them in the magbead plate
    for i in range(num_samples):
        p300.pick_up_tip()
        for j in range(sample_volume//300):
            p300.transfer(300, initial_samples[i].top(-38), mag_samples[i], new_tip='never')
        p300.transfer(sample_volume%300, initial_samples[i].top(-38), mag_samples[i], mix_after=(2, 300), new_tip='never')
        p300.blow_out(mag_samples[i])
        p300.drop_tip()
    sample_volume += 40

    # Add binding buffer
    for sample in mag_samples:
        p300.pick_up_tip()
        for i in range(binding_buffer_amount//300):
            p300.transfer(300,binding_buffer.top(-depth),sample, new_tip='never')
        p300.transfer(binding_buffer_amount%300,binding_buffer.top(-depth),sample, new_tip='never',mix_after=(3, 300))
        p300.drop_tip()
    sample_volume += binding_buffer_amount

    # Incubate with magbeads
    for i in range(magbead_incubation_time):
        protocol.delay(seconds=30)
        for sample in mag_samples:
            p300.pick_up_tip()
            p300.mix(1,300,sample.top(-20))
            p300.drop_tip()


    # Engage Magnetic Module Gen 2 to bind DNA
    mag_module.engage(height_from_base=5)
    protocol.delay(seconds=90)

    # Transfer supernatant to waste
    for sample in mag_samples:
        p300.flow_rate.aspirate=50
        p300.pick_up_tip()
        for i in range(sample_volume//300):
            p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.transfer(sample_volume%300, sample.top(-depth), waste, new_tip='never')
        p300.drop_tip()
    
    # Wash the beads with twice, and then let it dry
    
    # The following blocks until air drying represent different wash conditions. Make sure the appropriate ones are implemented
    
    # Wash with X% ethanol twice
    for sample in Eth_wash:
        for _ in range(2):
            p300.pick_up_tip()
            p300.transfer(300, ethanol.top(-depth), sample, mix_after=(3, 200), new_tip='never')
            protocol.delay(seconds=15)
            p300.transfer(300,sample.top(-depth),waste, new_tip='never')
            p300.drop_tip()



    # Air dry for 6 minutes
    protocol.delay(minutes=6)

    # Disengage Magnetic Module Gen 2 to release DNA
    mag_module.disengage()

    # Transfer elution buffer to the sample
    for sample in mag_samples:
        p300.pick_up_tip()
        p300.transfer(30, elution_buffer.top(-34), sample, mix_after=(5, 10), new_tip='never')
        p300.blow_out(sample.top())
        p300.drop_tip()

    # Incubate for 2 minutes
    protocol.delay(minutes=2)

    # Engage Magnetic Module Gen 2 to bind DNA again
    mag_module.engage(height_from_base=5)

    # Incubate with magbeads
    protocol.delay(minutes=1)

    # Transfer eluted DNA to a new well
    for i in range(num_samples):
        p300.pick_up_tip()
        p300.transfer(30, mag_samples[i].top(-depth), elute_samples[i], new_tip='never')
        p300.drop_tip()

    # Disengage Magnetic Module Gen 2
    mag_module.disengage()
