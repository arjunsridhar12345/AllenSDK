"""Module for writing NWB files for the Visual Behavior Neuropixels project"""

import logging
import sys
import argschema
import marshmallow
from allensdk.brain_observatory.ecephys.vbn_corbett_ecephys_session import \
    VBNCorbettEcephysSession
from allensdk.brain_observatory.ecephys.write_nwb.nwb_writer import \
    VBNCorbettEcephysNwbWriter
from allensdk.brain_observatory.ecephys.write_nwb.vbn_opto._schemas import \
    VBNOptoInputSchema, OutputSchema


def main():
    args = sys.argv[1:]
    try:
        parser = argschema.ArgSchemaParser(
            args=args,
            schema_type=VBNOptoInputSchema,
            output_schema_type=OutputSchema,
        )
        logging.info('Input successfully parsed')
    except marshmallow.exceptions.ValidationError as err:
        logging.error('Parsing failure')
        logging.error(err)
        raise err

    nwb_writer = VBNCorbettEcephysNwbWriter(
        session_nwb_filepath=parser.args['output_path'],
        session_data=parser.args['session_data'],
        serializer=VBNCorbettEcephysSession
    )

    try:
        nwb_writer.write_nwb_dynamic_gating_session(skip_probes=parser.args['skip_probes'])
        logging.info('File successfully created')
    except Exception as err:
        logging.error('NWB write failure')
        logging.error(err)
        raise err


if __name__ == "__main__":
    main()
