# imports
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Alginate Bead Preparation (OT-2, multi-channel)',
    "author": "",
    'description': '',
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# Runtime Parameters (Recommended)
def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name = "bead_size",
        display_name = "Bead Size",
        description = "",
        default = 50,
        minimum = 20,
        maximum = 300,
        unit = "µL"
    )
    parameters.add_int(
        variable_name = "bead_num",
        display_name = "Bead Amount",
        description = "",
        default = 50,
        minimum = 8,
        maximum = 560,        
    )
    parameters.add_int(
        variable_name = "available_res",
        display_name = "Filled slots on the reservoir (left to right)",
        description = "",
        default = 1,
        minimum = 1,
        maximum = 12,        
    )
    parameters.add_bool(
        variable_name = "debug",
        display_name = "Debugging Mode",
        description = "",
        default = False
    )

def run(protocol: protocol_api.ProtocolContext):
     # labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    bath = protocol.load_labware('nest_96_wellplate_200ul_flat','2')
    res = protocol.load_labware('nest_12_reservoir_15ml','3')

     # pipettes
    p300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[tiprack])

     # loaction definitions
    dest = bath.wells_by_name()['A4']
     # commands
    bead_size = protocol.params.bead_size
    bead_num = protocol.params.bead_num
    available_res = protocol.params.available_res
    if  not protocol.params.debug:
        # Protocol goes here
        if (14*available_res) < (0.3*bead_num):
            raise ValueError("Not enough alginate solution")
        available = [14.0 for i in range(available_res)]
        current_reservoir = 0
        beads = 0
        names = {'A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12'}
        p300.pick_up_tip()
        while beads < bead_num:
            if available[current_reservoir] < 2.4:
                current_reservoir += 1
            else:
                origin = res.wells_by_name()[names[current_reservoir]].top(-vol_to_height(available[current_reservoir]))
                p300.transfer(bead_size, origin, dest, new_tip='never')
                available[current_reservoir] -= (0.008*bead_size)
                beads += 8
        p300.drop_tip()
    else:
        #Debugging code goes here
        p300.pick_up_tip()
        a = res.wells_by_name()['A1']
        b = res.wells_by_name()['A2']
        vol = 15.0
        while vol > 1:
            p300.transfer(300, a.top(-vol_to_height(vol)),b,new_tip='never')
        p300.drop_tip()
    
def vol_to_height(vol):
    full_depth = 37
    return round(-2.467*vol + full_depth)