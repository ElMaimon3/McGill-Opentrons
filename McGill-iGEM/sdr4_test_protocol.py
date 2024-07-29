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

liquids_file = '\sdr4_liquids.csv'
buffer_file = '\sdr4_buffer.csv'

def load_computer():
    '''
    Load assay strands/gates information from csv files 
    '''
    # csv (sdr4_liquids) with liquid rack mapping and volume (uL/reaction) for each liquid type (except buffer)
    # for each strand/gate: 
        # source (where on rack) 
        # volume (uL/condition) for reaction 
        # volume in tube (uL)
        # its associated memory_number
        # type (restoration, reporter, sum, sum_low, output, output_fuel, buffer)
        # buffer (memory = 0), has no volume for reaction, only source
    # csv (sdr4_buffer) table with memory, condition, volume of buffer for reaction    
    
        
    # liquids = {memory_number : {"type": {"source":, "volume for reaction":}}}
    # e.g. pipette.transfer(liquids[memory_number]["type"]["volume"], liquids[memory_number]["type"]["source"], well mapping)
    
    # iterate through csv and populate liquids
    
    # buffer = {memory_number : {"condition": "volume for reaction":}}
    # define buffer amount for each memory for each condition
    # define tube for each liquid
    # return liquids, buffer
    
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

def map_plate():
    
    # for each memory, name/define each condition well (single/duplicate/triplicate)
    return

def plate_buffer():
    
    # with p1000, same tip for all buffer 
    # --> all buffer with same tip (if enough) (no need to mix on dispense)
    return

def add_parameters(parameters: protocol_api.Parameters):
    
    '''set parameters to deciced how the protocol will run'''
    # i.e. to specify acceptable values and to inform the protocol user what the parameter does
    
    # (int) Number of memories --> affects num of flurophores/reporters --> affects num to be plated and the last well with comobo of reporters
    # (int) single/duplicate/triplicate --> ...
    # (bool) dry run?
    # boundaries for volumes?
    
# run protocol
def run(protocol: protocol_api.ProtocolContext):
    
    # load tube rack, p1000 single, p20 single, 96 plate
    
    # load computer
    # map plate
    
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
