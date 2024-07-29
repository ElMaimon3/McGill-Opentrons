from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "SDR4 Test",
    "description": "Restroration Testing - validating:  Sum strand + restoration gate → release of output strand → trigger release of reporter strand from reporter gate",
    "author": "Yaman Al Janaideh <yaman.aljanaideh@mail.mcgill.ca>"
}

# run requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

def load_computer():
    """
    Load assay strands/gates information from CSV files.

    This function reads two CSV files: 'sdr4_liquids.csv' and 'sdr4_buffer.csv'.
    It extracts information about the liquid volumes required for each condition 
    in an assay and the buffer volumes needed for each memory and condition.

    The 'sdr4_liquids.csv' file should contain the following columns:
    - memory_number: The memory number associated with the liquid.
    - liquid_type: sdr4 liquids (restoration, reporter, sum, sum_low, output, output_fuel, buffer).
    - liquid_source: The source position on the rack where the liquid is located.
    - liquid_total_volume: The total volume of the liquid in the source tube (uL).
    - liquid_reaction_volume: The volume of the liquid required per reaction (uL).

    The 'sdr4_buffer.csv' file should contain the following columns:
    - memory_number: The memory number associated with the buffer.
    - condition_number: The condition number within the memory.
    - buffer_well_volume: The volume of buffer needed for the well (uL).

    The function returns two dictionaries:
    - liquids: A dictionary where the keys are memory numbers and the values are 
      dictionaries containing liquid types and their associated source wells and volumes.
      Example: 
      {
          1: {
              "reporter": {"source": "A1", "liquid_total_volume": 1000, "liquid_reaction_volume": 1.0},
              "restoration": {"source": "A2", "liquid_total_volume": 1000, "liquid_reaction_volume": 3.8},
              ...
          },
          ...
      }
    
    - buffer: A dictionary where the keys are memory numbers and the values are 
      dictionaries containing condition numbers and their associated buffer volumes.
      Example: 
      {
          1: {
              1: 99.0,
              2: 98.0,
              ...
          },
          ...
      }
    
    Returns:
        dict: A dictionary containing liquid information for each memory --> liquids[memory][liquid_type] = {source, liquid_total_volume, liquid_reaction_volume}
        dict: A dictionary containing buffer volumes for each memory and condition --> buffer[memory][condition] = buffer_well_volume
    """
    liquids_file = '\sdr4_liquids.csv'
    buffer_file = '\sdr4_buffer.csv'
    
    liquids = {}
    buffer = {}
    
    # Load liquids data
    with open(liquids_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            memory_number = int(row["memory_number"])
            liquid_type = row['liquid_type']
            source = row['liquid_source']
            liquid_total_volume = float(row['liquid_total_volume'])
            liquid_reaction_volume = float(row['liquid_reaction_volume'])
            
            if memory_number not in liquids: liquids[memory_number] = {}
            
            liquids[memory_number][liquid_type] = {
                "source": source,
                "liquid_total_volume": liquid_total_volume,
                "liquid_reaction_volume": liquid_reaction_volume
            }
        
    # Load buffer data
    with open(buffer_file, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            memory_number = int(row["memory_number"])
            condition_number = int(row['condition_number'])
            buffer_well_volume = float(row['buffer_well_volume'])
            
            if memory_number not in buffer: buffer[memory_number] = {}
            
            buffer[memory_number][condition_number] = buffer_well_volume
                  
    return liquids, buffer

def map_plate(num_replicates, num_memories):
    
    """
    Map each memory's conditions to specific wells on a 96-well plate. i.e destination well for each memory and condition.

    Args:
        num_replicates (int): Number of replicates (1 for single, 3 for triplicate).
        num_memories (int): Number of memories/fluorophores to plate for.
        
    Returns:
        dict: A dictionary mapping each memory and condition to specific wells --> plate_map[memory][condition] = well
    """
    plate_map = {}
    plate_rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    plate_cols = list(range(1, 13))
    
    col_index = 0
    for memory in range(1, num_memories+1):
        plate_map[memory] = {}
        for condition in range(1, 7): # 6+1
            if num_replicates == 1:
                plate_map[memory][condition] = f"{plate_rows[condition-1]}{plate_cols[col_index]}"
            elif num_replicates == 3:
                plate_map[memory][condition] = [
                    f"{plate_rows[condition-1]}{plate_cols[col_index]}",
                    f"{plate_rows[condition-1]}{plate_cols[col_index+1]}",
                    f"{plate_rows[condition-1]}{plate_cols[col_index+2]}"
                ]  
        col_index += 3 if num_replicates == 3 else 1
        
    return plate_map

def plate_buffer():
    
    # with p1000, same tip for all buffer 
    # --> all buffer with same tip (if enough) (no need to mix on dispense)
    return

def add_parameters(parameters: protocol_api.Parameters):
    """
    Set parameters to decide how the protocol will run.

    This function allows users to specify acceptable values and inform the protocol
    on how it should execute. Parameters include:
    - Number of replicates (single or triplicate)
    - Whether to perform a dry run
    - Tube depth
    - Well depth

    """
    parameters.add_int(
        variable_name = "number_of_replicates",
        display_name = "Number of replicates",
        description = "Number of replicates for each condition (single or triplicate)",
        defualt = 1,
        choices = [
            {"display_name": "Single", "value": 1},
            {"display_name": "Triplicate", "value": 3}
        ]
    )
    
    parameters.add_boolean(
        variable_name = "dry_run",
        display_name = "Dry run",
        description = "Run the protocol without actual liquid handeling",
        default = False
    )
    
    parameters.add_int(
        variable_name = "number_of_memories",
        display_name = "Number of memories",
        description = "Number of memories/fluorophores to plate for",
        default = 1
    )
    
    parameters.add_float(
        variable_name = "eppendorf_depth",
        display_name = "Eppendorf depth",
        description = "",
        default = 36.5,
        minimum = 1.0,
        maximum = 60.0,
        unit = "mm"
    )
    
    parameters.add_float(
        variable_name = "well_depth",
        display_name = "Well depth",
        description = "",
        default = 14.4,
        minimum = 1.0,
        maximum = 60.0,
        unit = "mm"
    )
    
# run protocol
def run(protocol: protocol_api.ProtocolContext):
    
    # load tube rack, p1000 single & tips, p20 single & tips, p300 tips, 96 plate
    liquid_eppendorf_rack = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '2')
    
    tiprack_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', '7')
    p1000_single = protocol.load_instrument('p1000_single_gen2', 'left', tips_racks = [tiprack_1000])
    
    tiprack_10 = protocol.load_labware('opentrons_96_tiprack_10ul', '1')
    p20_single = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack_10])
    
    plate_96 = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '4')
    
    # load computer
    liquids, buffer = load_computer()
    
    # map plate
    num_replicates = protocol.parameters['num_replicates']
    num_memories = protocol.parameters['num_memories']
    plate_map = map_plate(num_replicates, num_memories)
    
    # wait for user to switch p1000 out for multichannel p300 (protocol.pause('Please switch the p1000 to a multichannel p300 pipette and press resume'))
    # load multichannel p300
    
    
    # adjust the well_bottom_clearance param to set the distance above the well bottom for dispensing
    # plate mapping for each for each memory (single/duplicate/triplicate)
    # with p20 single and new tip always for each liquid_type (hover dispense, no mixing on dispense)
    # --> all restoration for a memory --> next memory's restoration...
    # --> all reporter for a memory --> next memory's reporter...
    # --> all sum/sumlow for a memory --> next memory's sum/sum_low...
    # --> output for a memory --> next memory's output...
    # --> all outputfuel for a memory --> next memory's outputfuel...
    
    # with p300 multichannel and new tip for each row
    # --> mix all wells 
    
    return
