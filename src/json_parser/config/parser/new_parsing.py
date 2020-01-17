#!/usr/bin/env python3

import sys
from util.util import read_json_file
from util.log import ProjectLogger
from config.util.special_keys import OPTIONAL_KEYS
import json
import logging

class Parser:
    def __init__(self, job_id="NA", debug_mode=False):
        # Initialize the project logger
        if debug_mode:
            self.project_logger = ProjectLogger(job_id, "parser.parsing.Parser", logging.DEBUG)
        else:
            self.project_logger = ProjectLogger(job_id, "parser.parsing.Parser")
        self.job_id = job_id

    def read_input_file(self, file_path):
        try:
            with open(file_path, "r") as F:
                return F.read().splitlines()
        except FileNotFoundError:
            self.project_logger.log_error("E.par.Fil.1", 'Input file "' + str(file_path) + '" could not be found')
            sys.exit(1)

    @staticmethod
    def remove_comments(input_lines):
        """
         Remove any comment lines from the list of lines

           A comment line is a line where the first non-whitespace character is a '#'
        """
        filtered_lines = []
        for line in input_lines:
            if line != "":
                # If the first non-space character is a '#', exclude it
                if len(line.strip()) > 0 and line.strip()[0] != '#':
                    filtered_lines.append(line)
        return filtered_lines

    @staticmethod
    def clean_input_file(input_lines):
        """
         Takes in a list of input lines, and removes any blank and comment lines (lines beginning with '#')
        """
        # Remove all blank lines
        non_empty_lines = list(filter(None, input_lines))
        return Parser.remove_comments(non_empty_lines)

    @staticmethod
    def is_json_file(afile):
        lines=open(afile,'r')
        outcome=False
        for eachLine in lines:
            content=eachLine.strip()
            if len(content)>0:
                if content[0]=='{':
                    outcome=True
                break
        return outcome

    def create_key_value_pairs(self, input_lines, file_path):
        """
        Turns a list of lines with keys and values separated by a '=' into pairs of (key, value) tuples
        """
        key_value_pairs = []

        for line in input_lines:
            if "=" not in line:
                self.project_logger.log_error(
                    "E.par.NEq.1",
                    "No equals sign present in line '" + line + "' from input file '" + file_path + "'"
                )
                sys.exit(1)
            else:
                # Get the position of the first equals sign (assumes there is no '=' in the key name)
                split_pos = line.index("=")
                key = line[0:split_pos]
                value = line[split_pos + 1:]
                key_value_pairs.append((key, value))
        return key_value_pairs

    def validate_key_value_pairs(self, key_value_pairs, file_path):
        """
         Takes in a list of (Key, Value) tuples, and confirms that they are valid (or throws an error)

        Keys that are allowed to be empty are not checked (see src/config/util/special_keys.py)

         Checks performed:
            1. Verifies that all Keys have an associated Value
            2. Verifies that the Value is enclosed in double quotes
            3. Verifies that no special characters are present in the Values
            4. Verifies that no Key is present more than once
            5. Verifies that no value is whitespace only
        """
        # List comprehensions to create complete list of keys
        keys_list = [k for k, v in key_value_pairs]

        for key, value in key_value_pairs:
            if key.lower() in OPTIONAL_KEYS and (value == "" or value == '""'):
                # These keys are allowed to have empty values, do not perform checking (simply write a debug message)
                self.project_logger.log_debug(
                    "The key '" + key + "' had an empty value; since its value is optional, no error was thrown"
                )
            else:
                # Check that the value is not empty
                if value == '':
                    self.project_logger.log_error(
                        "E.par.NVa.1",
                        "No value present for key '" + key + "' in input file '" + file_path + "'"
                    )
                # Check that the value is enclosed in double quotes
                elif value[0] != '"' or value[-1] != '"':
                    self.project_logger.log_error(
                        "E.par.NQt.1",
                        "No quotes around the value for key '" + key + "' in input file '" + file_path + "'"
                    )
                # Check to see that non-whitespace are present between the quote marks
                #   value[1:-1] trims off the first and last chars and strip removes all whitespace chars from the ends
                elif value[1:-1].strip() == '':
                    self.project_logger.log_error(
                        "E.par.WhS.1",
                        "Only whitespace found in value '" + value + "' of key '" + key + "' in input file '" +
                        file_path + "'"
                    )
                # Check if any special characters are present
                special_chars = "!#$%&()*;<>?@[]^`{|}~"
                for special_char in special_chars:
                    if special_char in value:
                        self.project_logger.log_error(
                            "E.par.SpC.1",
                            "Invalid special character '" + special_char + "' found in value '" + value +
                            "' of key '" + key + "' in input file '" + file_path + "'"
                        )
                # Check whether any key is present multiple times
                if keys_list.count(key) > 1:
                    self.project_logger.log_error(
                        "E.par.Key.1", "Key '" + key + "' is present more than once in input file '" + file_path + "'"
                    )
                else:
                    self.project_logger.log_debug("The key-value pair '" + key + "=" + value + "' is a valid pair")

    @staticmethod
    def comp_match_depth(phrase_query, phrase_target):
        word1=phrase_query.split('.')
        word2=phrase_target.split('.')
        if word1[-1]!=word2[-1]:
            return 0
        else:
            n=len(word1)
            m=len(word2)
            if m<n:
                n=m
            depth=1.0
            for i in range(1,n):
                if word1[-1-i]!=word2[-1-i]:
                    break
                else:
                    depth=1.0+float(i)
        return depth-(float(m)-depth)/100.0

    def new_insert_values_into_dict(self, starting_dict, key_value_dict):
        output_dict = {}
        for key in starting_dict:
            max_depth=0
            for target_key in key_value_dict:
                depth=Parser.comp_match_depth(key,target_key)
                if depth>max_depth:
                    output_dict[key]=key_value_dict[target_key]
                    max_depth=depth
            if max_depth==0:
                ttt=0
                self.project_logger.log_error(
                    "E.par.NoJ.1",
                    "The '" + key + "' key in the JSON template did not have a corresponding key in any of the " +
                    "config files; this key was not filled in"
                )
            else:         
                if starting_dict[key].find("Array")!=-1:
                    if not isinstance(output_dict[key], list):
                        output_dict[key]=output_dict[key].split(",")
        return output_dict

    def new_fill_in_json_template(self, input_file_list, json_template_file, output_file):
        template_dict = read_json_file(json_template_file, self.project_logger,
                                       json_not_found_error_code="E.par.JSN.1",
                                       json_bad_format_error_code="E.par.JSN.2"
                                       )
        all_key_value_pairs={} 
        for input_file in input_file_list:
            if Parser.is_json_file(input_file):
                 cur_dict=read_json_file(input_file, self.project_logger,
                                       json_not_found_error_code="E.par.JSN.1",
                                       json_bad_format_error_code="E.par.JSN.2"
                                       )
                 # Add the current key-value pairs to the overall key-value dictionary
                 for key, value in cur_dict.items():
                     all_key_value_pairs[key]=value

            else:
                 raw_input_lines = self.read_input_file(input_file)
                 input_lines = self.clean_input_file(raw_input_lines)
                 # Turn input lines into Tuples of Key-Value pairs
                 key_value_tuples = self.create_key_value_pairs(input_lines, file_path=input_file)
                 # Validate the key-value entries (Returns nothing; only possible outputs are error messages)
                 self.validate_key_value_pairs(key_value_tuples, file_path=input_file)

                 # Add the current key-value paris to the overall key-value dictionary
                 for pair in key_value_tuples:
                     all_key_value_pairs[pair[0]]=pair[1][1:-1]
        template_dict = self.new_insert_values_into_dict(template_dict,all_key_value_pairs)

        # Write the python dictionary out as a JSON file in the output file location
        with open(output_file, "w") as updated_json:
            json.dump(template_dict, updated_json, indent=4, sort_keys=True)

        # Exit if errors have occurred
        if self.project_logger.errors_issued > 0:
            self.project_logger.log_info(
                'Configuration file parser failed with ' + str(self.project_logger.errors_issued) + ' error(s) issued'
            )
            sys.exit(1)
        else:
            # Write a success message to the log
            self.project_logger.log_info(
                    'Configuration file parser finished successfully with ' + str(self.project_logger.warnings_issued) +
                    ' warning(s) issued'
            )
