#
# Copyright (c) 2022 Intel Corporation
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

.PHONY: setup_repository

default: setup_repository

BUILD_CUSTOM_NODE=false

setup_repository:
# Download horizontal text detection model
	mkdir -p workspace/horizontal-text-detection-0001/1
	curl https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/horizontal-text-detection-0001/FP32/horizontal-text-detection-0001.bin -o workspace/horizontal-text-detection-0001/1/horizontal-text-detection-0001.bin
	curl https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/horizontal-text-detection-0001/FP32/horizontal-text-detection-0001.xml -o workspace/horizontal-text-detection-0001/1/horizontal-text-detection-0001.xml
# Download text recognition model
	mkdir -p workspace/text-recognition-0014/1
	curl https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/text-recognition-0014/FP32/text-recognition-0014.bin -o workspace/text-recognition-0014/1/text-recognition-0014.bin
	curl https://storage.openvinotoolkit.org/repositories/open_model_zoo/2022.1/models_bin/2/text-recognition-0014/FP32/text-recognition-0014.xml -o workspace/text-recognition-0014/1/text-recognition-0014.xml
ifeq ($(BUILD_CUSTOM_NODE),true)
# Build custom node
	cd ../../../src/custom_nodes && \
	make BASE_OS=ubuntu NODES=horizontal_ocr && \
	mkdir -p ../../demos/horizontal_text_detection/python/workspace/lib && \
	mv lib/ubuntu/libcustom_node_horizontal_ocr.so ../../demos/horizontal_text_detection/python/workspace/lib/libcustom_node_horizontal_ocr.so
endif
# Copy configuration file to workspace directory
	cp config.json workspace/.
ifeq ($(BUILD_CUSTOM_NODE),false)
	sed -i 's:\/workspace\/lib\/libcustom_node_horizontal_ocr.so:\/ovms\/lib\/custom_nodes\/libcustom_node_horizontal_ocr.so:g' workspace/config.json
endif
clean:
	@rm -rf workspace