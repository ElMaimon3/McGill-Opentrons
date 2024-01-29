# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (OT-2)

# Import necessary modules
from opentrons import protocol_api

# Metadata
metadata = {
    'protocolName': 'Pellet-Free Minipreps with Magbeads (OT-2)',
    'author': 'Your Name',
    'description': 'Opentrons protocol for pellet-free minipreps with magbeads (OT-2)',
    'apiLevel': '2.15'
}

# Define the protocol
def run(protocol: protocol_api.ProtocolContext):
    depth = 12#depth to take supernatant from plate
    time_offset = 140 #to make sure no sample is incubated more than 5 minutes

    # Load labware
    plate_96 = protocol.load_labware('nest_96_wellplate_2ml_deep', '1')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '2')
    reagent_reservoir = protocol.load_labware('nest_12_reservoir_15ml', '3')
    mag_module = protocol.load_module('magnetic module gen2', '4')
    mag_plate = mag_module.load_labware('corning_48_wellplate_1.6ml_flat')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', '6')

    # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', '5')])
    p20 = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=[protocol.load_labware('opentrons_96_filtertiprack_20ul', '10')])

    # Define sample locations on the 96-well plate
    num_samples = 2
    initial_samples = plate_96.wells('A3','A4')  # Adjust the slice to match your sample locations
    mag_samples = mag_plate.wells('A3','A4')
    elute_samples = elute_plate.wells('A3','A4')

    # Define reagent locations on the tube rack
    lysis_buffer = reagent_reservoir['A5']
    neutralization_buffer = reagent_reservoir['A6']
    ethanol = reagent_reservoir['A7']
    magbeads = tube_rack['A1']

    # Define waste location
    waste = reagent_reservoir['A12']

    # Define elution buffer location
    elution_buffer = reagent_reservoir['A8']

    # Perform miniprep protocol

    #add lysis buffer to samples
    for sample in initial_samples:
        # Transfer lysis buffer to the sample
        p300.pick_up_tip()
        p300.transfer(150, lysis_buffer.bottom(-12), sample, new_tip='never')
        p300.mix(5, 200, sample)
        p300.blow_out(sample)
        p300.drop_tip()

    #let it incubate for 5 minutes
    protocol.delay(seconds=(300-time_offset))
    ##Should add a minutes - x seconds per sample so then the first sample doesn't incubate for more than 5 minutes

    #transfer neutralization buffer to the samples
    for sample in initial_samples:
        #transfer neutralization buffer to the samples
        p300.pick_up_tip()
        p300.transfer(150, neutralization_buffer.bottom(-12), sample, new_tip='never')
        p300.mix(5, 200, sample)
        p300.blow_out(sample)
        p300.drop_tip()
    
    #now we have to add magnetic beads to the plate on the mag module
    for sample in mag_samples:
        p300.flow_rate.aspirate=50
        p300.pick_up_tip()
        p300.transfer(50, magbeads.top(-34), sample, new_tip='never')
        p300.blow_out(sample)
        p300.drop_tip()
    
    #take bacterial samples and put them in the magbead plate
    for i in range(num_samples):
        p300.pick_up_tip()
        p300.transfer(300, initial_samples[i], mag_samples[i], mix_after=(5, 100), new_tip='never') ##check that it transfers to the right place
        p300.blow_out(mag_samples[i])
        p300.drop_tip()


    # Incubate with magbeads for 5 minutes
    protocol.delay(minutes=5) #make the amount of time a variable to change easily. 

    # Engage Magnetic Module Gen 2 to bind DNA
    mag_module.engage(height_from_base=5)

    #transfer supernatant to waste
    for sample in mag_samples:
        p300.flow_rate.aspirate=50
        p300.pick_up_tip()
        p300.transfer(300, sample.top(-depth), waste, new_tip='never')
        p300.drop_tip()
    
    #now we need to wash the beads with ethanol twice, and then let it dry

    for sample in mag_samples:
    # Wash with 70% ethanol twice
        for _ in range(2): #CHECK THIS LINE OF CODE
            p300.pick_up_tip()
            p300.transfer(200, ethanol.bottom(-12), sample, mix_after=(3, 200), new_tip='never')
            protocol.delay(minutes=1) ##CHECK THESE TWO LINES OF CODE FOR FUNCTIONALITY
            p300.transfer(200,sample.top(-depth),waste)
            p300.blow_out(waste) #Does not work indented (is this most efficient)
            p300.drop_tip()

    # Air dry for 5 minutes
    protocol.delay(minutes=5)

    # Disengage Magnetic Module Gen 2 to release DNA
    mag_module.disengage()

    # Transfer elution buffer to the sample
    for sample in mag_samples:
        p300.pick_up_tip()
        p300.transfer(20, elution_buffer.bottom(-12), sample, mix_after=(5, 10), new_tip='never')
        p300.blow_out(sample.top())
        p300.drop_tip()

    # Incubate for 2 minutes
    protocol.delay(minutes=2)

    # Engage Magnetic Module Gen 2 to bind DNA again
    mag_module.engage(height_from_base=5)

    # Incubate with magbeads for 2 minutes
    protocol.delay(minutes=1)

    # Transfer eluted DNA to a new well
    for sample, elute_sample in mag_samples, elute_samples:
        p300.pick_up_tip()
        p300.transfer(20, sample.bottom(1), elute_sample, new_tip='never')
        p300.drop_tip()

    # Disengage Magnetic Module Gen 2
    mag_module.disengage()
