# Opentrons Protocol for Pellet-Free Minipreps with Magbeads (Flex, 8-Channel)
from opentrons import protocol_api
from opentrons.protocol_api import SINGLE, PARTIAL_COLUMN, ALL
from typing import List, Dict, Tuple, Optional

metadata = {
    'protocolName': 'Pellet-Free Minipreps with Magbeads (Flex, 8-Channel)',
    "author": "Gabriel Straface, Dan Voicu (Ignea Lab @ McGill University) - Adapted for Flex",
    'description': '''Opentrons protocol for pellet-free minipreps with magbeads (Flex). Requires 940uL of culture, 500uL of concentrated lysis buffer, 
    250uL of concentrated neutralization buffer, 300uL of binding buffer, 40uL of magbeads, 600uL of wash per sample. Uses 8-channel pipettes with intelligent tip management.''',
}
requirements = {"robotType": "Flex", "apiLevel": "2.21"}


def reservoir_vol_to_height(vol: float) -> float:
    '''Convert volume to height for 12-well reservoir (22mL wells).'''
    if vol < 1:
        raise ValueError('Reservoir volume too low!')
    # Approximate function for 22mL reservoir wells
    return round(-2.5*vol + 50)

class NotEnoughTips(Exception):
    '''Exception raised when there aren't enough tips available.'''
    pass

def smart_pick_up(size: int, tips: Optional[Dict[str, bool]] = None) -> Tuple[str, Dict[str, bool]]:
    '''Selects the appropriate tips based on the number needed.'''
    if tips is None:
        tips = {f"{chr(65+row)}{col+1}": True for row in range(8) for col in range(12)}

    def is_column_clear(column, start_row):
        for row in range(start_row):
            loc = f"{chr(65+row)}{column+1}"
            if tips.get(loc, False):
                return False
        return True

    # Iterate over columns
    for col in range(12):
        if size == 1:
            for row in range(7, -1, -1):
                loc = f"{chr(65+row)}{col+1}"
                if tips.get(loc, False) and is_column_clear(col, row):
                    tips[loc] = False
                    return loc, tips

        elif 2 <= size <= 7:
            for row in range(8 - size + 1):
                if all(tips.get(f"{chr(65+row+i)}{col+1}", False) for i in range(size)) and is_column_clear(col, row):
                    loc = f"{chr(65+row+size-1)}{col+1}"
                    for i in range(size):
                        tips[f"{chr(65+row+i)}{col+1}"] = False
                    return loc, tips

        elif size == 8:
            if all(tips.get(f"{chr(65+row)}{col+1}", False) for row in range(8)):
                loc = f"A{col+1}"
                for row in range(8):
                    tips[f"{chr(65+row)}{col+1}"] = False
                return loc, tips

    raise NotEnoughTips("Not enough tips available")

def configure_pipette_for_group(pipette, group_size: int, last_size: int):
    '''Configures the pipette nozzle layout based on the group size.'''
    keep_tips = (group_size == last_size)
    
    if not keep_tips:
        if group_size == 1:
            pipette.configure_nozzle_layout(
                style=SINGLE,
                start="H1"
            )
        elif group_size == 8:
            pipette.configure_nozzle_layout(
                style=ALL
            )
        else:
            last = ["G1", "F1", "E1", "D1", "C1", "B1"][group_size-2]
            pipette.configure_nozzle_layout(
                style=PARTIAL_COLUMN,
                start="H1",
                end=last
            )
    
    return keep_tips, group_size

def group_wells_by_column(wells: List[str]) -> List[List[str]]:
    '''Groups wells by column and sorts by size.'''
    # Group wells by column
    column_groups = {}
    for well in wells:
        col = well[1:]  # Extract column number
        if col not in column_groups:
            column_groups[col] = []
        column_groups[col].append(well)
    
    # Sort wells within each column by row
    for col in column_groups:
        column_groups[col].sort(key=lambda x: ord(x[0]))
    
    # Convert to list of groups and sort by size
    grouped_wells = list(column_groups.values())
    return sorted(grouped_wells, key=len, reverse=True)

def run(protocol: protocol_api.ProtocolContext):
    # Load waste chute
    waste_chute = protocol.load_waste_chute()
    
    # Load labware
    initial_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 'A2')
    small_tube_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 'B2')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 'C2')
    elute_plate = protocol.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 'C1')
    
    # Load modules
    temp_module = protocol.load_module('temperatureModuleV2', 'D1')  # Specified but unused
    mag_block = protocol.load_module('magneticBlockV1', 'D2')
    mag_plate = mag_block.load_labware('nest_96_wellplate_2ml_deep')
    heater_shaker = protocol.load_module('heaterShakerModuleV1', 'A3')
    hs_plate = heater_shaker.load_labware('nest_96_wellplate_2ml_deep')
    
    # Load pipettes and tip racks
    p50 = protocol.load_instrument('flex_8channel_50', 'left', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3')
    ])
    p300 = protocol.load_instrument('flex_8channel_1000', 'right', tip_racks=[
        protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'B3'),
        protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'B1')  # B1 is free from thermocycler
    ])
    
    # SETTINGS MUST BE ADJUSTED FOR EACH RUN
    # Define available reagents (mL):
    available_lysis = 15.0
    available_neutralization = 15.0  
    available_binding = 15.0
    available_PB = 15.0
    available_PE = 15.0
    available_ethanol = 15.0
    
    # Define sample wells - organize by column for 8-channel efficiency
    sample_wells = ['D1','D2','D3','E1','E2','E3','E4','F1','F2','F3','F4']
    
    # Group samples by column for efficient pipetting
    grouped_wells = group_wells_by_column(sample_wells)
    
    # Define reagent locations in reservoir
    lysis_buffer = reservoir['A1']
    neutralization_buffer = reservoir['A2'] 
    binding_buffer = reservoir['A3']
    PB = reservoir['A4']
    PE = reservoir['A5']
    ethanol = reservoir['A6']
    
    # Small reagents in tube racks
    magbeads = small_tube_rack['A1']
    elution_buffer = small_tube_rack['A2']
    P = small_tube_rack['A3']  # For regular samples
    N = small_tube_rack['A4']  # For regular samples
    
    # Define sample categories
    regular_wells = ['D1','D2','D3']
    conc_wells = ['E1','E2','E3','E4','F1','F2','F3','F4']
    
    # Wash settings - map each well to its wash protocol
    wash_protocols = {
        'D1': 'two_wash', 'D2': 'two_wash', 'D3': 'two_wash', 'E1': 'two_wash', 'F1': 'two_wash',
        'E2': 'PB_wash', 'F2': 'PB_wash',
        'E3': 'PE_wash', 'F3': 'PE_wash', 
        'E4': 'eth_wash', 'F4': 'eth_wash'
    }
    
    # Protocol parameters
    depth = 39  # Depth to take supernatant from deep plate
    magbead_incubation_time = 5  # Total minutes
    sample_volume = 940
    lysis_buffer_amount = 470
    neutralization_buffer_amount = 239
    binding_buffer_amount = 301
    
    # Initialize tip tracking
    tips_50 = None
    tips_300 = None
    
    # Helper function for single well operations
    def transfer_to_single_wells(pipette, source, wells, volume, tip_rack, tips_dict, mix_after=None):
        '''Transfer to individual wells using single tip pickup.'''
        pipette.configure_nozzle_layout(style=SINGLE, start="H1")
        
        for well in wells:
            if tips_dict is None:
                tips_dict = {f"{chr(65+row)}{col+1}": True for row in range(8) for col in range(12)}
            
            tip_loc, tips_dict = smart_pick_up(1, tips_dict)
            pipette.pick_up_tip(tip_rack.wells_by_name()[tip_loc])
            
            if isinstance(source, str):  # Source is a tube rack location
                source_well = small_tube_rack[source]
                pipette.transfer(volume, source_well.top(-37), initial_plate[well], new_tip='never')
            else:
                pipette.transfer(volume, source, initial_plate[well], new_tip='never')
                
            if mix_after:
                pipette.mix(mix_after[0], mix_after[1], initial_plate[well])
            pipette.blow_out(initial_plate[well])
            pipette.drop_tip()
            
        return tips_dict

    protocol.comment("Starting pellet-free miniprep protocol...")
    
    # Step 1: Add lysis buffer to samples
    protocol.comment("Adding lysis buffer...")
    
    # Regular samples get buffer from small tubes
    tips_50 = transfer_to_single_wells(
        p50, 'A3', regular_wells, 250, 
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3'), tips_50,
        mix_after=(1, 200)
    )
    
    # Concentrated samples get buffer from reservoir  
    for well in conc_wells:
        if tips_300 is None:
            tips_300 = {f"{chr(65+row)}{col+1}": True for row in range(8) for col in range(12)}
        
        p300.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_300 = smart_pick_up(1, tips_300)
        p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
        
        # Add lysis buffer in portions
        for i in range(lysis_buffer_amount//300):
            p300.transfer(300, lysis_buffer.top(-reservoir_vol_to_height(available_lysis)), 
                         initial_plate[well], new_tip='never')
            available_lysis -= 0.3
        
        remaining = lysis_buffer_amount % 300
        if remaining > 0:
            p300.transfer(remaining, lysis_buffer.top(-reservoir_vol_to_height(available_lysis)), 
                         initial_plate[well], new_tip='never')
            available_lysis -= remaining/1000
            
        p300.mix(1, 300, initial_plate[well])
        p300.blow_out(initial_plate[well])
        p300.drop_tip()
    
    sample_volume += lysis_buffer_amount
    
    # Incubation time calculation
    time_offset = 60 * len(sample_wells)
    if time_offset < 300:
        protocol.delay(seconds=(300-time_offset))
    
    # Step 2: Add neutralization buffer
    protocol.comment("Adding neutralization buffer...")
    
    # Regular samples
    tips_50 = transfer_to_single_wells(
        p50, 'A4', regular_wells, 250,
        protocol.load_labware('opentrons_flex_96_tiprack_50ul', 'C3'), tips_50,
        mix_after=(5, 200)
    )
    
    # Concentrated samples
    for well in conc_wells:
        p300.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_300 = smart_pick_up(1, tips_300)
        p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
        
        p300.transfer(neutralization_buffer_amount, 
                     neutralization_buffer.top(-reservoir_vol_to_height(available_neutralization)),
                     initial_plate[well], new_tip='never')
        available_neutralization -= neutralization_buffer_amount/1000
        p300.mix(2, 300, initial_plate[well])
        p300.blow_out(initial_plate[well])
        p300.drop_tip()
    
    sample_volume += neutralization_buffer_amount
    
    # Incubate 10 minutes
    protocol.delay(minutes=10)
    
    # Step 3: Add magnetic beads to mag plate
    protocol.comment("Adding magnetic beads to magnetic plate...")
    p50.configure_nozzle_layout(style=SINGLE, start="H1")

    default_p50_aspirate = p50.flow_rate.aspirate
    for well in sample_wells:
        tip_loc, tips_50 = smart_pick_up(1, tips_50)
        p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
        p50.flow_rate.aspirate = 50
        p50.mix(3, 40, magbeads.top(-37))
        p50.transfer(40, magbeads.top(-37), mag_plate[well], new_tip='never')
        p50.blow_out(mag_plate[well])
        p50.drop_tip()
    p50.flow_rate.aspirate = default_p50_aspirate

    # Step 4: Transfer samples to magnetic plate
    protocol.comment("Transferring samples to magnetic plate...")
    
    for well in sample_wells:
        p300.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_300 = smart_pick_up(1, tips_300)
        p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
        
        # Transfer in portions
        for j in range(sample_volume//300):
            p300.transfer(300, initial_plate[well].top(-38), mag_plate[well], new_tip='never')
        
        remaining = sample_volume % 300
        if remaining > 0:
            p300.transfer(remaining, initial_plate[well].top(-38), mag_plate[well], 
                         mix_after=(2, 300), new_tip='never')
        
        p300.blow_out(mag_plate[well])
        p300.drop_tip()
    
    sample_volume += 40
    
    # Step 5: Add binding buffer
    protocol.comment("Adding binding buffer...")
    
    for well in sample_wells:
        p300.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_300 = smart_pick_up(1, tips_300)
        p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
        
        for i in range(binding_buffer_amount//300):
            p300.transfer(300, binding_buffer.top(-reservoir_vol_to_height(available_binding)),
                         mag_plate[well], new_tip='never')
            available_binding -= 0.3
        
        remaining = binding_buffer_amount % 300
        if remaining > 0:
            p300.transfer(remaining, binding_buffer.top(-reservoir_vol_to_height(available_binding)),
                         mag_plate[well], new_tip='never', mix_after=(3, 300))
            available_binding -= remaining/1000
        
        p300.drop_tip()
    
    sample_volume += binding_buffer_amount
    
    # Step 6: Incubate with magbeads using heater-shaker
    protocol.comment("Moving plate to heater-shaker for magbead incubation...")
    protocol.move_labware(
        labware=mag_plate,
        new_location=heater_shaker,
        use_gripper=True
    )
    
    heater_shaker.close_labware_latch()
    heater_shaker.set_and_wait_for_shake_speed(rpm=1000)
    
    # Shake for magbead incubation
    protocol.delay(minutes=magbead_incubation_time)
    
    heater_shaker.deactivate_shaker()
    heater_shaker.open_labware_latch()
    
    # Move plate back to magnetic block
    protocol.comment("Moving plate back to magnetic block...")
    protocol.move_labware(
        labware=mag_plate,
        new_location=mag_block,
        use_gripper=True
    )
    
    # Allow beads to settle
    protocol.delay(seconds=90)
    
    # Step 7: Remove supernatant
    protocol.comment("Removing supernatant...")

    default_p300_aspirate = p300.flow_rate.aspirate
    for well in sample_wells:
        p300.configure_nozzle_layout(style=SINGLE, start="H1")
        p300.flow_rate.aspirate = 50
        tip_loc, tips_300 = smart_pick_up(1, tips_300)
        p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])

        for i in range(sample_volume//300):
            p300.transfer(300, mag_plate[well].top(-depth), waste_chute, new_tip='never')

        remaining = sample_volume % 300
        if remaining > 0:
            p300.transfer(remaining, mag_plate[well].top(-depth), waste_chute, new_tip='never')

        p300.drop_tip()
    p300.flow_rate.aspirate = default_p300_aspirate

    # Step 8: Wash cycles based on protocol
    protocol.comment("Performing wash cycles...")
    
    def perform_wash(wells, wash_buffer, buffer_tracker, wash_name, num_washes=1):
        '''Perform wash steps for specified wells.'''
        nonlocal tips_300
        
        for well in wells:
            for wash_num in range(num_washes):
                # Add wash buffer
                p300.configure_nozzle_layout(style=SINGLE, start="H1")
                tip_loc, tips_300 = smart_pick_up(1, tips_300)
                p300.pick_up_tip(p300.tip_racks[0].wells_by_name()[tip_loc])
                
                p300.transfer(300, wash_buffer.top(-reservoir_vol_to_height(buffer_tracker)),
                             mag_plate[well], mix_after=(3, 200), new_tip='never')
                protocol.delay(seconds=15)
                p300.transfer(300, mag_plate[well].top(-depth), waste_chute, new_tip='never')
                p300.drop_tip()
                
                buffer_tracker -= 0.3
                
                # Remove excess with p50
                p50.configure_nozzle_layout(style=SINGLE, start="H1")
                tip_loc, tips_50 = smart_pick_up(1, tips_50)
                p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
                p50.transfer(20, mag_plate[well].top(-depth), waste_chute, new_tip='never')
                p50.drop_tip()
        
        return buffer_tracker
    
    # Group wells by wash protocol
    two_wash_wells = [w for w in sample_wells if wash_protocols.get(w) == 'two_wash']
    pb_wash_wells = [w for w in sample_wells if wash_protocols.get(w) == 'PB_wash']
    pe_wash_wells = [w for w in sample_wells if wash_protocols.get(w) == 'PE_wash']
    eth_wash_wells = [w for w in sample_wells if wash_protocols.get(w) == 'eth_wash']
    
    # Perform different wash protocols
    if two_wash_wells:
        available_PB = perform_wash(two_wash_wells, PB, available_PB, "PB", 1)
        available_PE = perform_wash(two_wash_wells, PE, available_PE, "PE", 1)
    
    if pb_wash_wells:
        available_PB = perform_wash(pb_wash_wells, PB, available_PB, "PB", 2)
    
    if pe_wash_wells:
        available_PE = perform_wash(pe_wash_wells, PE, available_PE, "PE", 2)
    
    if eth_wash_wells:
        available_ethanol = perform_wash(eth_wash_wells, ethanol, available_ethanol, "ethanol", 2)
    
    # Air dry
    protocol.delay(minutes=6)
    
    # Step 9: Elution
    protocol.comment("Adding elution buffer...")
    
    for well in sample_wells:
        p50.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_50 = smart_pick_up(1, tips_50)
        p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
        
        p50.transfer(30, elution_buffer.top(-34), mag_plate[well], 
                    mix_after=(5, 10), new_tip='never')
        p50.blow_out(mag_plate[well].top())
        p50.drop_tip()
    
    # Incubate
    protocol.delay(minutes=2)
    
    # Let beads settle
    protocol.delay(minutes=1)
    
    # Step 10: Transfer eluted DNA
    protocol.comment("Transferring eluted DNA to final plate...")
    
    for well in sample_wells:
        p50.configure_nozzle_layout(style=SINGLE, start="H1")
        tip_loc, tips_50 = smart_pick_up(1, tips_50)
        p50.pick_up_tip(p50.tip_racks[0].wells_by_name()[tip_loc])
        
        p50.transfer(30, mag_plate[well].top(-depth), elute_plate[well], new_tip='never')
        p50.drop_tip()
    
    protocol.comment("Miniprep protocol complete!")