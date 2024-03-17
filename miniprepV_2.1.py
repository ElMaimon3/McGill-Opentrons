# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (OT-2)

# Import necessary modules
from opentrons import protocol_api

# Metadata
metadata = {
    'protocolName': 'Pellet-Free Minipreps with Magbeads (OT-2)',
    'author': 'Your Name',
    'description': '''Opentrons protocol for pellet-free minipreps with magbeads (OT-2). Requires XuL of culture, XuL of concentrated lysis buffer, 
    XuL of concentrated neutralization buffer, XuL of magbeads, XuL of wash per sample. DO NOT FORGET TO TURN ON THE HEPA FAN ON MAX''',
    'apiLevel': '2.15'
}

# Define the protocol
def run(protocol: protocol_api.ProtocolContext):
    depth = 39#depth to take supernatant from plate
    magbead_incubation_time  = 10 # Total, minutes
    sample_volume = 900
    lysis_buffer_amount = 450
    neutralization_buffer_amount = 450

    # Load labware
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap','9')
    plate_96 = protocol.load_labware('nest_96_wellplate_2ml_deep', '1')
    tube_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '2')
    reagent_reservoir = protocol.load_labware('nest_12_reservoir_15ml', '3')
    mag_module = protocol.load_module('magnetic module gen2', '4')
    mag_plate = mag_module.load_labware('nest_96_wellplate_2ml_deep')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', '6')

    # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5'),protocol.load_labware('opentrons_96_tiprack_300ul', '11')])
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_tiprack_20ul', '8')])


    # Define sample locations on the 96-well plates
    initial_samples = plate_96.wells('D1','D2','D3','E1','E2','E3','E4','F1','F2','F3','F4')  # Adjust the slice to match your sample locations
    regular_samples = plate_96.wells('D1','D2','D3')
    conc_samples = plate_96.wells('E1','E2','E3','E4','F1','F2','F3','F4')
    mag_samples = mag_plate.wells('D1','D2','D3','E1','E2','E3','E4','F1','F2','F3','F4')
    elute_samples = elute_plate.wells('D1','D2','D3','E1','E2','E3','E4','F1','F2','F3','F4')
    num_samples = len(initial_samples)
    if len(mag_samples) != len(initial_samples) or len(initial_samples) != len(elute_samples):
        raise ValueError("The amount of samples in each plate are not the same!")

    
    # Define how to wash samples (can be removed for final implementation)
    Two_wash = mag_plate.wells('D1','D2','D3','E1','F1')
    PB_wash = mag_plate.wells('E2','F2')
    PE_wash = mag_plate.wells('E3','F3')
    Eth_wash = mag_plate.wells('E4','F4')

    # Define reagent locations on the tube rack
    lysis_buffer = tube_rack['A1']
    neutralization_buffer = tube_rack['B1']
    PB = tube_rack['A2']
    magbeads = small_tube_rack['A1']
    PE = tube_rack['B2']
    ethanol = tube_rack['C2']
    P = small_tube_rack['A3']
    N = small_tube_rack['A4']

    # Define waste location
    waste = reagent_reservoir['A12']

    # Define elution buffer location
    elution_buffer = small_tube_rack['A5']

    # Perform miniprep protocol

    #add lysis buffer to samples
    for sample in regular_samples:
        p300.pick_up_tip()
        p300.transfer(250, P.top(-37), sample, new_tip='never')
        p300.mix(5, 300, sample)
        p300.blow_out(sample)
        p300.drop_tip()

    for sample in conc_samples:
        # Transfer lysis buffer to the sample
        p300.pick_up_tip()
        p300.transfer(300, lysis_buffer.top(-37), sample, new_tip='never')
        p300.transfer(150, lysis_buffer.top(-37), sample, new_tip='never')
        p300.mix(5, 300, sample)
        p300.blow_out(sample)
        p300.drop_tip()

    # Calculate time offset x
    if num_samples>8:
        num_steps = num_samples//8
        if num_samples%8==0:
            time_offset = 60*num_steps
        else:        
            time_offset = 60*(num_steps+1)
    #else:
    time_offset = 60*num_samples 
    if time_offset<300:
        protocol.delay(seconds=(300-time_offset))

    #transfer neutralization buffer to the samples
    for sample in regular_samples:
        p300.pick_up_tip()
        p300.transfer(250, N.top(-37), sample, new_tip='never')
        p300.mix(5, 300, sample)
        p300.blow_out(sample)
        p300.drop_tip()

    for sample in conc_samples:
        #transfer neutralization buffer to the samples
        p300.pick_up_tip()
        p300.transfer(300, neutralization_buffer.top(-37), sample, new_tip='never')
        p300.transfer(150, neutralization_buffer.top(-37), sample, new_tip='never')
        p300.mix(6, 300, sample)
        p300.blow_out(sample)
        p300.drop_tip()
        
    #now we have to add magnetic beads to the plate on the mag module
    p300.pick_up_tip()
    for sample in mag_samples:
        p300.flow_rate.aspirate=50
        p300.mix(3,50,magbeads.top(-37))
        p300.transfer(50, magbeads.top(-37), sample, new_tip='never')
        p300.blow_out(sample)
    p300.drop_tip()
    
    #take bacterial samples and put them in the magbead plate
    for i in range(num_samples):
        p300.pick_up_tip()
        p300.transfer(300, initial_samples[i].top(-38), mag_samples[i].top(-depth), mix_after=(1, 300), new_tip='never') ##check that it transfers to the right place    
        p300.transfer(300, initial_samples[i].top(-38), mag_samples[i].top(-depth), mix_after=(1, 300), new_tip='never') ##check that it transfers to the right place
        p300.transfer(300, initial_samples[i].top(-38), mag_samples[i].top(-depth), mix_after=(1, 300), new_tip='never') ##check that it transfers to the right place    
        p300.transfer(300, initial_samples[i].top(-38), mag_samples[i].top(-depth), mix_after=(5, 300), new_tip='never') ##check that it transfers to the right place
        p300.blow_out(mag_samples[i])
        p300.drop_tip()

    # Incubate with magbeads
    for i in range(magbead_incubation_time):
        protocol.delay(seconds=40)
        for sample in mag_samples:
            p300.pick_up_tip()
            p300.mix(1,300,sample)
            p300.drop_tip()


    # Engage Magnetic Module Gen 2 to bind DNA
    mag_module.engage(height_from_base=5)
    protocol.delay(seconds=40)

    #transfer supernatant to waste
    for sample in mag_samples:
        p300.flow_rate.aspirate=50
        p300.pick_up_tip()
        p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.transfer(50, sample.top(-depth), waste, new_tip='never')
        p300.drop_tip()
    
    #now we need to wash the beads with twice, and then let it dry

    # for sample in mag_samples: 
    # Previous line is commented out for the purpose of testing which way of washing works better. uncomment for final implementation
    
    # The following blocks until air drying are duplicated and the top performing one should be kept after tests
    # Wash with PB then PE
    for sample in Two_wash:
        p300.pick_up_tip()
        p300.transfer(300, PB.top(-34), sample, mix_after=(3, 200), new_tip='never')
        protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
        p300.transfer(300,sample.top(-depth),waste, new_tip='never')
        p300.drop_tip()
        p300.pick_up_tip()
        p300.transfer(300, PE.top(-34), sample, mix_after=(3, 200), new_tip='never')
        protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
        p300.transfer(300,sample.top(-depth),waste, new_tip='never')
        p300.drop_tip()
        # Remove excess
        p20.pick_up_tip()
        p20.transfer(20,sample.top(-depth),waste, new_tip='never')
        p20.drop_tip()

    # Wash with PB twice
    for sample in PB_wash:
        for _ in range(2): #CHECK THIS LINE OF CODE
            p300.pick_up_tip()
            p300.transfer(300, PB.top(-34), sample, mix_after=(3, 200), new_tip='never')
            protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
            p300.transfer(300,sample.top(-depth),waste, new_tip='never')
            p300.drop_tip()
        # Remove excess
        p20.pick_up_tip()
        p20.transfer(20,sample.top(-depth),waste, new_tip='never')
        p20.drop_tip()

    # Wash with PE twice
    for sample in PE_wash:
        for _ in range(2): #CHECK THIS LINE OF CODE
            p300.pick_up_tip()
            p300.transfer(300, PE.top(-34), sample, mix_after=(3, 200), new_tip='never')
            protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
            p300.transfer(300,sample.top(-depth),waste, new_tip='never')
            p300.drop_tip()
        # Remove excess
        p20.pick_up_tip()
        p20.transfer(20,sample.top(-depth),waste, new_tip='never')
        p20.drop_tip()

    # Wash with X% ethanol twice
    for sample in Eth_wash:
        for _ in range(2): #CHECK THIS LINE OF CODE
            p300.pick_up_tip()
            p300.transfer(300, ethanol.top(-34), sample, mix_after=(3, 200), new_tip='never')
            protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
            p300.transfer(300,sample.top(-depth),waste, new_tip='never')
            p300.drop_tip()
        # Remove excess ethanol
        p20.pick_up_tip()
        p20.transfer(20,sample.top(-depth),waste, new_tip='never')
        p20.drop_tip()


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

    # Incubate with magbeads for 2 minutes
    protocol.delay(minutes=1)

    # Transfer eluted DNA to a new well
    for i in range(num_samples):
        p300.pick_up_tip()
        p300.transfer(30, mag_samples[i].top(-depth), elute_samples[i], new_tip='never')
        p300.drop_tip()

    # Disengage Magnetic Module Gen 2
    mag_module.disengage()
