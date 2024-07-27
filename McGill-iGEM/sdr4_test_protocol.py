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

     
def add_parameters(parameters: protocol_api.Parameters):
    
    '''set parameters to deciced how the protocol will run'''
    # i.e. to specify acceptable values and to inform the protocol user what the parameter does
    
    # (int) Number of memories --> affects num of flurophores/reporters --> affects num to be plated and the last well with comobo of reporters
    # (int) single/duplicate/triplicate --> ...
    # (bool) dry run?

    
# run protocol
def run(protocol: protocol_api.ProtocolContext):
    
    '''get info'''
    # csv with assay strands/gates
    # for each strand/gate: 
        # source (where on rack) 
        # volume (uL) for reaction 
        # its associated memory_number
        # type (restoration, reporter, sum, sum_low, output, reporter_top, outputfuel)    
    
        
    # liquids = {"memory_number" : {"type": {"source":, "volume for reaction":}}}
    # e.g. pipette.transfer(liquids["memory_number"]["type"]["volume"], liquids["memory_number"]["type"]["source"], mapping)
    
    # iterate through csv and populate liquids
    
    # define buffer 
        
    # load tube rack, p1000 single, p20 single, 96 plate
    
    # for each memory, name/define each condition well (single/duplicate/triplicate)
    
    # plate mapping
    # with p1000, same tip for all buffer 
    # --> all buffer with same tip (if enough) (no need to mix on dispense)
    
    # wait for user to switch p1000 out for multichannel p300 (protocol.pause('Please switch the p1000 to a multichannel p300 pipette and press resume'))
    # load multichannel p300
    
    # plate mapping for each for each memory (single/duplicate/triplicate)
    # with p20 single and new tip always for each liquid_type (hover dispense, no mixing on dispense)
    # --> all restoration for a memory --> next memory's restoration...
    # --> all reporter for a memory --> next memory's reporter...
    # --> all sum/sumlow for a memory --> next memory's sum/sum_low...
    # --> output for a memory --> next memory's output...
    # --> reporter_top for a memory + the extra well if there is another memory --> next memory's reporter_top + in the mix well...
    # --> all outputfuel for a memory --> next memory's outputfuel...
    
    # with p300 multichannel and new tip for each row
    # --> mix all wells 
    
