from opentrons import protocol_api

metadata = {
    'protocolName': 'Miniprep multi channel debug',
    'author': 'Your Name',
    'description': '''''',
    'apiLevel': '2.15'
}

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
    initial_samples = plate_96.wells('A6')
    mag_samples = mag_plate.wells('A6')
    elute_samples = elute_plate.wells('A6')
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
