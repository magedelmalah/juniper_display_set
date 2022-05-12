#!/usr/bin/python

#
# Copyright (c) 2017 carles.kishimoto@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.

import argparse
import re
import os

def print_set_command(lcommands, leaf):
    #print(("%s %s" % (" ".join(lcommands), leaf)))
    return ("%s %s\n" % (" ".join(lcommands), leaf))

def clean_nso_text_file(raw_text_data, start, end):
    start_pattern = re.compile(start)
    end_pattern = re.compile(end)
    start_index = start_pattern.search(raw_text_data).start()
    end_index = end_pattern.search(raw_text_data).start()
    raw_text_data = raw_text_data[start_index:end_index]
    raw_text_data = re.sub(start_pattern, '', raw_text_data)
    raw_text_data = re.sub('\+\s+# .*\n','',raw_text_data)  # to remove lines in nso commit dry-run like #  first/after, etc..
    raw_text_data = raw_text_data.replace("&lt;*>", "<*>")
    return raw_text_data

def get_set_config(filein, ignore_annotations, input_type_nso, set_output):
    all_set_commands = ""
    try:
        if not os.path.exists(set_output):
            os.makedirs(set_output)
    except IOError:
        print("Cannot create output diectory:", set_output)
        exit()
    try:
        with open(filein, 'r') as f:
            data = f.read()
    except IOError:
        print("Error: Could not read input file:", filein)
        exit()
    if input_type_nso:
        data = clean_nso_text_file(data, start='             junos:configuration {\n', end="                 }\n             }\n         }\n     }\n }\n services {")
    
    data = re.sub(r'\s+\S+\s\{\s\.\.\.\s\}','', data) # to remove line like SC-VPLS-1G { ... }
    # Add \n for one-line configs
    data = data.replace("{", "{\n").replace("}", "\n}")

    # Keep a list of annotations to be printed at the end
    lannotations = []
    annotation = ""
    lres = ["set"]

    for elem in data.split("\n"):
        elem = elem.strip()
        if elem.startswith("-") and lres[0]=="set":
            lres[0]="delete"
            elem = re.sub("^\-", "", elem)
        elif elem.startswith("+"):
            elem = re.sub("^\+", "", elem)
        if elem.startswith("[edit"):
            elem = elem.replace("[edit ", "").replace("]","").replace("[edit","")
            lres = [lres[0]]
        if elem == "" or elem.startswith("#") or re.search("\S+\@\S+\>", elem):
            continue    
        if elem.startswith("/*"):
            # Store current annotation
            annotation = elem.replace("/* ", '"').replace(" */", '"')
        else:
            clean_elem = elem.strip("\t\n\r{ ")
            if annotation:
                lannotations.append("top")
                if len(lres) > 1:
                    level = lres[:]
                    # Replace "set" with "edit"
                    level[0] = "edit"
                    lannotations.append("%s" % " ".join(level))
                # Annotation in a leaf, keep only the keyword
                if ";" in clean_elem:
                    clean_elem = clean_elem.split()[0]
                lannotations.append("annotate %s %s" % (clean_elem, annotation))
                annotation = ""  
            if "inactive" in clean_elem:
                clean_elem = clean_elem.replace("inactive: ", "")
                linactive = list(lres)
                linactive[0] = "deactivate"                    
                all_set_commands = all_set_commands + print_set_command(linactive, clean_elem)
            if "protect" in clean_elem:
                clean_elem = clean_elem.replace("protect: ", "")
                lprotect = list(lres)
                lprotect[0] = "protect"
                all_set_commands = all_set_commands + print_set_command(lprotect, clean_elem)
            if ";" in clean_elem:  # this is a leaf
                # below if to remove duplicate value in edit and next child
                all_set_commands = all_set_commands + print_set_command(lres, clean_elem.split(";")[0])
                print(lres)
            elif clean_elem == "}":  # Up one level remove parent
                lres.pop()
            else:
                lres.append(clean_elem)
    output =  ".\\" + set_output + "\\" +  filein.split("\\")[2]
    if os.path.exists(output):
        os.remove(output)
    with open(output, 'a') as f:
        f.write(all_set_commands)    

    if not ignore_annotations:
        # Print all annotations at the end
        for a in lannotations:
            print(a)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=">>> Juniper display set")
    parser.add_argument(
        "--ignore-annotations",
        required=False,
        default=False,
        action='store_true',
        help="Specify if annotations should be removed from the output",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=str,
        help="Specify the input Junos configuration file",
    )
    parser.add_argument(
        "--nso",
        default=False,
        type=str,
        help="Specify if the file from cisco nso commit dry-run ",
    )
    parser.add_argument(
        "--output",
        default="set_output",
        type=str,
        help="Specify the output Junos configuration directory",
    )
    
    args = parser.parse_args()

    get_set_config(args.input, args.ignore_annotations, args.nso, args.output)
