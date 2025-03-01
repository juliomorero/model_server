#
# Copyright (c) 2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import numpy as np
from tensorflow import make_tensor_proto, make_ndarray, expand_dims
import datetime
import argparse
import math
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc
from kaldi_python_io import ArchiveReader
import json
import requests
import importlib

spec = importlib.util.spec_from_loader('client_utils', importlib.machinery.SourceFileLoader('client_utils', '../../common/python/client_utils.py'))
client_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_utils)

def print_debug(msg):
    global debug_mode
    if debug_mode:
        print(msg)


def calculate_utterance_error(referenceArray, resultArray):
    root_mean_err = math.sqrt(
        (np.square(
            resultArray -
            referenceArray)).mean(
            axis=None))
    return root_mean_err


def create_request(inputs):
    signature = "serving_default"
    data_obj = {"signature_name": signature,'inputs': inputs}
    data_json = json.dumps(data_obj)
    return data_json


def parse_arguments():
    # Example commands:
    # RM_LSTM4F
    # rest_stateful_client.py --input_path rm_lstm4f/test_feat_1_10.ark --score_path rm_lstm4f/test_score_1_10.ark
    #     --rest_url http://localhost --rest_port 5555 --input_name Parameter:0 --output_name affinetransform:0
    #     --model_name rm_lstm4f --debug

    # ASPIRE_TDNN
    # rest_stateful_client.py --input_path aspire_tdnn/mini_feat_1_10.ark,aspire_tdnn/mini_feat_1_10_ivector.ark
    #     --score_path aspire_tdnn/aspire_tdnn_mini_feat_1_10_kaldi_score.ark
    #     --rest_url http://localhost --rest_port 5555 --input_name input,ivector --output_name Final_affine
    #     --model_name aspire_tdnn --cw_l 17 --cw_r 12 --debug

    parser = argparse.ArgumentParser(
        description='Sends requests via rest API using data in stateful model ark input file. '
        'It displays performance statistics and average rms errors comparing results with reference scores.'
        'Optionally you can enable debug mode to print additional information about inputs and outputs and detailed accuracy numbers.')
    parser.add_argument(
        '--input_path',
        required=False,
        default='rm_lstm4f/test_feat_1_10.ark',
        help='Path to input ark file')
    parser.add_argument(
        '--score_path',
        required=False,
        default='rm_lstm4f/test_score_1_10.ark',
        help='Path to reference scores ark file')
    parser.add_argument(
        '--rest_port',
        required=False,
        default=5555,
        help='Specify port to rest service. default: 5555')
    parser.add_argument(
        '--rest_url',
        required=False,
        default='http://localhost',
        help='Specify url to REST API service. default: http://localhost')
    parser.add_argument(
        '--input_name',
        required=False,
        default='Parameter:0',
        help='Specify input tensor name. default: Parameter:0')
    parser.add_argument(
        '--output_name',
        required=False,
        default='affinetransform:0',
        help='Specify output name. default: affinetransform:0')
    parser.add_argument(
        '--model_name',
        default='rm_lstm4f',
        help='Define model name, must be same as is in service. default: rm_lstm4f',
        dest='model_name')
    parser.add_argument(
        '--debug',
        required=False,
        default=0,
        help='Enabling debug prints. Set to 1 to enable debug prints. Default: 0')
    parser.add_argument(
        '--cw_l',
        required=False,
        default=0,
        help='Number of requests for left context window. Works only with context window networks. Default: 0')
    parser.add_argument(
        '--cw_r',
        required=False,
        default=0,
        help='Number of requests for right context window. Works only with context window networks. Default: 0')
    parser.add_argument(
        '--sequence_id',
        required=False,
        default=1,
        help='Sequence ID used by every sequence provided in ARK files. Setting to 0 means sequence will obtain its ID from OVMS. Default: 1')
    parser.add_argument(
        '--model_version',
         help='Model version to be used. Default: LATEST',
        type=int, dest='model_version')
    parser.add_argument(
        '--client_cert',
        required=False,
        default=None,
        help='Specify mTLS client certificate file. Default: None.')
    parser.add_argument(
        '--client_key',
        required=False,
        default=None,
        help='Specify mTLS client key file. Default: None.')
    parser.add_argument(
        '--ignore_server_verification',
        required=False,
        action='store_true',
        help='Skip TLS host verification. Do not use in production. Default: False.')
    parser.add_argument(
        '--server_cert',
        required=False,
        default=None,
        help='Path to a custom directory containing trusted CA certificates, server certificate, or a CA_BUNDLE file. Default: None, will use default system CA cert store.')
    print('### Starting rest_stateful_client.py client ###')

    args = vars(parser.parse_args())
    return args


def prepare_processing_data(args):
    delimiter = ","
    input_files = []
    reference_files = []
    input_names = []
    output_names = []
    input_paths = args.get('input_path').split(delimiter)
    for input_path in input_paths:
        print('Reading input ark file {}'.format(input_path))
        ark_reader = ArchiveReader(input_path)
        input_files.append(ark_reader)

    score_paths = args.get('score_path').split(delimiter)
    for score_path in score_paths:
        print('Reading scores ark file {}'.format(score_path))
        ark_reader = ArchiveReader(score_path)
        reference_files.append(ark_reader)

    inputs = args['input_name'].split(delimiter)
    for input in inputs:
        print('Adding input name {}'.format(input))
        input_names.append(input)

    outputs = args['output_name'].split(delimiter)
    for output in outputs:
        print('Adding output name {}'.format(output))
        output_names.append(output)

    # Validate input
    if len(input_files) != len(input_names):
        print(
            "ERROR: Number of input ark files {} must be equal to the number of input names {}".format(
                len(input_files),
                len(input_names)))
        exit(1)

    if len(reference_files) != len(output_names):
        print(
            "ERROR: Number of output ark files {} must be equal to the number of output names {}".format(
                len(reference_files),
                len(output_names)))
        exit(1)

    # Consolidate input
    input_data = dict()
    name_index = 0
    for ark_reader in input_files:
        input_name = input_names[name_index]
        input_sub_data = dict()
        for name_key, data_obj in ark_reader:
            sequence_size = data_obj.shape[0]
            data = list()
            for input_index in range(0, sequence_size):
                data.append(np.expand_dims(data_obj[input_index], axis=0))
            input_sub_data[name_key] = data
        input_data[input_name] = input_sub_data
        name_index += 1

    # Consolidate reference scores
    name_index = 0
    reference_scores = dict()
    for ark_score in reference_files:
        output_name = output_names[name_index]
        score_ojects = {k: m for k, m in ark_score}
        reference_scores[output_name] = score_ojects
        name_index += 1

    # First ark file is the one we will iterate through for all input ark
    # files per inference request input
    sequence_size_map = dict()
    for sequence_name, data in input_files[0]:
        sequence_size_map[sequence_name] = data.shape[0]
        # Validate reference output scores data for existing sequence names and shapes
        for name in reference_scores:
            score_objects = reference_scores[name]
            if score_objects[sequence_name].shape[0] != data.shape[0]:
                print(
                    "Error reference scores ark file doest not contain proper data for sequence name {0} and data shape {1}".format(
                        sequence_name, data.shape))
                exit(1)

    return sequence_size_map, input_names, output_names, input_data, reference_scores


def validate_output(result_dict, output_names):
    # Validate model output
    if "outputs" not in result_dict:
        print("ERROR: Invalid response format. Could not find \'outputs\' key")
        return False 
    results = result_dict["outputs"]
    if type(results) is not dict:
        print("ERROR: Invalid response format. No named format is not accepted for stateful models")
        return False 
    for output_name in output_names:
        if output_name not in results:
            print("ERROR: Invalid output name", output_name)
            print("Available outputs:")
            for o in results:
                print(o)
            return False
    if 'sequence_id' not in results:
        print("ERROR: Missing sequence_id in model output")
        print("Available outputs:")
        for o in results:
            print(o)
        return False
    elif type(results["sequence_id"]) is not list:
        print("ERROR: sequence_id received in inappropriate format")
        return False
    return True


def main():
    args = parse_arguments()
    global debug_mode
    debug_mode = int(args.get('debug'))
    certs = None
    verify_server = None
    if args.get('client_cert') is not None or args.get('client_key') is not None:
      if args.get('client_cert') is not None and args.get('client_key') is not None and args.get('rest_url').startswith("https"):
        certs = (args.get('client_cert'), args.get('client_key'))
        if args.get('server_cert') is not None:
          verify_server = args.get('server_cert')
        if args.get('ignore_server_verification') is True:
          verify_server = False
      else:
        print("Error: in order to use mTLS, you need to provide both --client_cert and --client_key. In addition, your --rest_url flag has to begin with 'https://'.")
        exit(1)

    processing_times = np.zeros((0), int)
    cw_l = int(args.get('cw_l'))
    cw_r = int(args.get('cw_r'))
    print('Context window left width cw_l: {}'.format(cw_l))
    print('Context window right width cw_r: {}'.format(cw_r))
    get_sequence_id = False
    sequence_id = np.uint64(args.get('sequence_id'))
    if sequence_id == 0:
        get_sequence_id = True
    print('Starting sequence_id: {}'.format(sequence_id))
    print('Start processing:')
    print('Model name: {}'.format(args.get('model_name')))
    version = ""
    if args.get('model_version') is not None:
        version = "/versions/{}".format(args.get('model_version'))

    sequence_size_map, input_names, output_names, input_data, reference_scores = prepare_processing_data(
        args)

    # Input control tokens
    SEQUENCE_START = 1
    SEQUENCE_END = 2

    global_avg_rms_error_sum = 0.0

    # Input shape information
    for input_name in input_names:
        input_sub_data = input_data[input_name]
        tensor_data = input_sub_data[list(sequence_size_map.keys())[0]][0]
        print_debug('\tInput {} in shape: {}'.format(input_name, tensor_data.shape))

    # Output shape information
    for output_name in output_names:
        score_data = reference_scores[output_name][list(sequence_size_map.keys())[0]][0]
        score_data = np.expand_dims(score_data, axis=0)
        print_debug('\tOutput {} in shape: {}'.format(output_name, score_data.shape))

    # Main inference loop
    session = requests.Session()
    for sequence_name, sequence_size in sequence_size_map.items():
        print('\n\tSequence name: {}'.format(sequence_name))
        print('\tSequence size: {}'.format(sequence_size))
        print('\tSequence id: {}'.format(sequence_id))

        if sequence_size == 1:
            print('\nERROR: Detected sequence with only one frame. Every sequence must contain at least 2 frames.'.format(
                sequence_size))
            exit(1)

        mean_avg_rms_error_sum = 0.0
        score_index = (cw_l + cw_r) * -1

        for x in range(0, sequence_size + cw_l + cw_r):
            print_debug('\tExecution: {}\n'.format(x))
            data_obj = {}
            inputs = dict()
            # Set input data index
            input_index = x
            # Input for context window
            if x < cw_l:
                # Repeating first frame infer request cw_l times for the
                # context window model start
                input_index = 0
            elif x >= cw_l and x < sequence_size + cw_l:
                # Standard processing
                input_index = x - cw_l
            else:
                # Repeating last frame infer request cw_r times for the
                # context window model end
                input_index = sequence_size - 1

            # Setting request input
            for input_name in input_names:
                input_sub_data = input_data[input_name]
                tensor_data = input_sub_data[sequence_name][input_index]
                inputs[input_name] = tensor_data.tolist()

            # Add sequence start
            if x == 0:
                inputs['sequence_control_input'] = [int(SEQUENCE_START)]

            # Set sequence id
            inputs['sequence_id'] = [int(sequence_id)]

            # Add sequence end
            if x == sequence_size + cw_l + cw_r - 1:
                inputs['sequence_control_input'] = [int(SEQUENCE_END)]

            #prepare request
            data_json = create_request(inputs)

            start_time = datetime.datetime.now()
            # result includes a dictionary with all model outputs
            result = session.post("http://{}:{}/v1/models/{}{}:predict".format(args['rest_url'], args['rest_port'], args['model_name'], version), data=data_json, cert=certs, verify=verify_server)
            end_time = datetime.datetime.now()

            try:
                result_dict = json.loads(result.text)
            except ValueError:
                print("The server response is not json format: {}",format(result.text))
                exit(1)
            if "error" in result_dict:
                print('Server returned error: {}'.format(result_dict))
                exit(1)

            if not validate_output(result_dict, output_names):
                print(
                    "ERROR: Model result validation error. Adding end sequence inference request for the model and exiting.")
                exit(1)

            result_dict = result_dict["outputs"]

            # Unique sequence_id provided by OVMS
            if get_sequence_id:
                sequence_id = np.uint64(result_dict['sequence_id'])
                get_sequence_id = False

            duration = (end_time - start_time).total_seconds() * 1000
            processing_times = np.append(
                processing_times, np.array([int(duration)]))

            # Compare results after we are pass initial context window results
            if score_index >= 0:
                # Loop over reference output results
                avg_rms_error_sum = 0.0

                for output_name in output_names:
                    score_data = reference_scores[output_name][sequence_name][score_index]

                    # Parse output
                    results_array = np.asarray(result_dict[output_name])

                    # Calculate error
                    avg_rms_error = calculate_utterance_error(
                        score_data, results_array[0])
                    avg_rms_error_sum += avg_rms_error

                    # Statistics
                    print_debug(
                        'Output name: {} Rms error: {:.10f}\n'.format(
                            output_name, avg_rms_error))

                mean_avg_rms_error_sum += avg_rms_error_sum
                # Statistics
                print_debug(
                    'Iteration {}; Average rms error: {:.10f} Processing time: {:.2f} ms; speed {:.2f} fps\n'.format(
                        x, avg_rms_error_sum, round(
                            np.average(duration), 2), round(
                            sequence_size / np.average(duration), 2)))
                # END output names loop

            score_index += 1
            # END utterance loop

        seq_avg_rms_error_sum = mean_avg_rms_error_sum / (sequence_size)
        print(
            "\tSequence id: {} ; Sequence name: {} ; Average RMS Error: {:.10f}\n".format(
                sequence_id,
                sequence_name,
                seq_avg_rms_error_sum))

        global_avg_rms_error_sum += seq_avg_rms_error_sum
        # END input name loop

    final_avg_rms_error_sum = global_avg_rms_error_sum / len(sequence_size_map)

    print("Global average rms error: {:.10f}\n".format(
        final_avg_rms_error_sum))
    client_utils.print_statistics(processing_times, sequence_size / 1000)
    print('### Finished rest_stateful_client.py client processing ###')


if __name__ == "__main__":
    main()
