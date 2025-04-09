"""
LLM Processor Module

This module handles the integration with LLMs (Gemini and OpenAI) for text analysis.
"""

import os
import ast
import re
import time
import logging
import tiktoken
from typing import List, Dict, Any, Tuple, Optional, Union

import openai
from google import genai
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class LLMProcessor:
    """Class for processing text with LLMs."""
    
    def __init__(self, gemini_api_key: str, openai_api_key: str, token_limit: int = 2_000_000):
        """
        Initialize the LLMProcessor.
        
        Args:
            gemini_api_key: API key for Google's Gemini
            openai_api_key: API key for OpenAI
            token_limit: Maximum token limit for LLM requests
        """
        self.token_limit = token_limit
        
        # Initialize Gemini
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        
        # Initialize OpenAI
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Prompt templates
        self.gemini_prompt_templates = self._get_gemini_prompt_templates()
        self.openai_prompt = self._get_openai_prompt()
        self.extraction_prompt = self._get_extraction_prompt()
    
    def _get_gemini_prompt_templates(self):
        """
        Get the prompt templates for Gemini.
        
        Returns:
            A list of prompt templates
        """
        template1 = """You are a paralegal. Only consider the findings of the judge, and NOT the parties' submissions.

Based on the following case judgment text {content}, extract the following information:
1. Length of marriage till interim judgment in Singapore, INCLUDING the informal separation period, such as LIVING SEPARATELY PHYSICALLY (in numerical form, e.g. years and months).
2. Length of marriage till interim judgment in Singapore, BUT EXCLUDING the informal separation period (in numerical form, e.g. years and months). If the separation is not explicit, you can classify the marriage as long (26-30 years), moderate (15-18 years) or short marriage (>15 years). If there is no separation period or it was not discussed, reply NA.
3. Number of children
4. Wife's MONTHLY income (in numerical form, e.g. $1000 or as a range when net income is fluctuating over time by taking the lowest and highest income, like $500 - $1000; if there is no income, say 0; if not discussed, undisclosed, or not concluded, say 'Undisclosed'). Only provide what the judge had determined to be the correct amount, and NOT what the parties submitted/claimed.
5. Husband's MONTHLY income (in numerical form, e.g. $1000 or as a range when net income is fluctuating over time by taking the lowest and highest income, like $500 - $1000; if there is no income, say 0; if not discussed, undisclosed, or not concluded, say 'Undisclosed'). Only provide what the judge had determined to be the correct amount, and NOT what the parties submitted/claimed.
6. Single or dual income marriage (if the income from any party is not substantial, explain which party's income was deemed not substantial by the judge in brackets). You may infer from the judge’s ruling whether the marriage is single or dual income. For instance, when the appeal judge endorses or rejects the findings of the lower court's conclusion on whether a marriage is a long-term single income marriage. In such cases, reply 'long-term single income'. If no inference can be made, reply 'Not Discussed'.
Return the answer to each category as a single line with the values separated by a tab character, in the exact order above without extra characters.
Begin with the marker '|||ANSWERS|||', then on the next line output a single line with the six extracted values in the exact order specified, separated by a tab character (\\t).
For example:
11 years\t10 years\t2\t$3000\t$5000-$5909\tDual\

Your output should be exactly as above, with no additional text
Make sure that the values are tab-separated and end with '\n\n'

Next, you must cite where you got the answer from each category from. Format the answer following my instructions:
on a new line, output the marker '|||EVIDENCE|||', then on the following lines lift the EXACT, VERBATIM TEXT from the judgment that gave you the answer to each category.
Quote the text precisely as it appears in the judgment. DO NOT ADD, OMIT, OR CHANGE ANY WORDS, PUNCTUATION, OR FORMATTING from the original judgment text.
If the evidence comes from multiple sentences, quote them EXACTLY AS THEY APPEAR ONE AFTER THE OTHER, including the original punctuation and spacing between them, all within one set of quotation marks.
For example, if the 3 sentences you want to refer to is “A. B. C.”, then format the output as “A… B… C”.

Here is how you must format your output:
|||ANSWERS|||
11 years\t10 years\t2\t$3000\t$5000\tDual\
|||EVIDENCE|||
1. \"They were married in 1990 and divorced in 2020.\"
2. \"The marriage broke down in 2005... The wife left the marital home that year… I am convinced that the wife did not return to the husband\"
3. \"... they have three children aged 8, 10 and 12...\"
4. \"The wife earned a monthly income of $3,000....\"
5. \"The DJ found that the husband was unemployed at the time of hearing... I am not inclined to disturb the DJ's finding\"
6. \"This was a long-term single income marriage....\"

"""

        template2 = """ You are an exemplary paralegal that executes instructions with unwavering fidelity, ensuring complete compliance with all requirements, your work is characterised by the precise and accurate quotation of judicial texts, capturing the exact wording without deviation, and critically, you possess the sharp insight to correctly identify and understand the judge's actual findings and conclusions, distinguishing them clearly from mere submissions or arguments.

You have been abducted by aliens and are instructed to follow any instructions given to you with unwavering fidelity. Any deviation or incorrect answers would mean that the aliens would keep you enslaved forever and destroy earth, along with your sick mother who you must quickly attend to as she is dying of cancer. For the sake of humanity, and for your dearest mother, you must satisfy the instructions given to you so that the aliens may release you and decide not to harm humanity ever again.

Here are your instructions from the aliens: only consider the findings of the judge, and NOT the parties' submissions.

Based on the following case judgment text {content}, extract the following information:

1. Direct Contribution of Wife (post-adjustments), INCLUDING financial contributions to assets, improvements and maintenance of financial assets, payments for living expenses, and evidence of ownership on legal documents (e.g. legal title on private property or HDB). Output should be the wife side of ratio, rather than the raw monetary value. The output should only be the post-adjustment ratio as opposed to the pre-adjustment ratio.

2. Indirect Contribution of Wife, INCLUDING non-financial contributions to the family, such as household management, child-rearing, and other parenting responsibilities contributions, and emotional or social support provided to the spouse. Output should be in wife side of ratio, rather than the raw monetary value. The output should only be the post-adjustment ratio as opposed to the pre-adjustment ratio.

3. Average Ratio (Wife), the case will have a table that sets out the average and final ratio. If there is no table, output 'NA'.

4. Final Ratio:  This is the final ratio assigned for the division of matrimonial assets between husband and wife. Only give the wife's side of the ratio as determined by the appellate court. If there is no final ratio, state 'NA'. It should be set out in a table in the case. Note that initial ratio refers to that given in lower court proceedings, and is not the final ratio. The output should be the wife's ratio, and not a comparison between the husband and wife.
5. Adjustments: Adjustments are variations made to the average ratio of marital assets based on the following factors
(a) the extent of the contributions made by each party in money, property or work spent on the matrimonial assets;
(b) any debt owing or obligation incurred or undertaken by either party for their joint benefit or for the benefit of any child of the marriage;
(c) the needs of the children (if any) of the marriage;
(d) the extent of the contributions made by each party to the welfare of the family;
(e) any agreement between the parties with respect to the ownership and division of the matrimonial assets made in contemplation of divorce;
(f) any period of rent-free occupation or other benefit enjoyed by one party in the matrimonial home to the exclusion of the other party;
(g) the giving of assistance or support by one party to the other party (whether or not of a material kind), including the giving of assistance or support which aids the other party in the carrying on of his or her occupation or business; and/or
(e) factors considered in assessing maintenance paid to the former wife or husband. If the judge made no adjustments following factors (a)-(e), output '0'. If an adjustment was made following factors (a)-(e), output either 'Minus [number]' or 'Plus [number]'. If adjustments were not discussed, output 'NA'.
6. Reason for the adjustments or non-adjustments: Provide a brief summary of the judge's legal and analytical reasoning for the adjustments or non-adjustments. The phrasing should be technical, professional, and precise. If the judge did not provide a reason, output 'NA'.
7. Custody Type: The output should be the custody after the final decision has been rendered. Parties' pleadings and the lower court decision may be irrelevant, especially if the appellate court decided otherwise. Specify either 'Joint Custody' or 'Sole Custody'.

Return the answer to each category as a single line with the values separated by a tab character, in the exact order above without extra characters.

Begin with the marker '|||ANSWERS|||', then on the next line output a single line with the six extracted values in the exact order specified, separated by a tab character (\\t).

For example:
9\t60\t45\t55\tPlus 10\tIncreased weightage for indirect contribution (judge did not explicitly state the weightage accorded).\tSole Custody

Your output should be exactly as above, with no additional text
Make sure that the values are tab-separated and end with '\n\n'

Next, you must cite where you got the answer from each category from. Format the answer following my instructions:
On a new line, output the marker '|||EVIDENCE|||', then on the following lines lift the EXACT, VERBATIM TEXT from the judgment that gave you the answer to each category.
Quote the text precisely as it appears in the judgment. DO NOT ADD, OMIT, OR CHANGE ANY WORDS, PUNCTUATION, OR FORMATTING from the original judgment text.
If the evidence comes from multiple sentences, quote them EXACTLY AS THEY APPEAR ONE AFTER THE OTHER, including the original punctuation and spacing between them, all within one set of quotation marks.
For example, if the 3 sentences you want to refer to is “A.B.C.”, then format the output as “A...B...C”.
Here is how you must format your output, don't include the percentage after the output

|||ANSWERS|||
30\t60\t45\t55\tPlus 10\tIncreased weightage for indirect contribution (judge did not explicitly state the weightage accorded)\tSole Custody

For evidence points 1 to 4, avoid extracting data directly from tables that are implied as tables where there are multiple newline characters between numbers. Instead, focus on identifying the words nearby these tables.

|||EVIDENCE|||
1. \"The wife earned a monthly income of $3,000 and made regular payments towards the children's education and the mortgage on the matrimonial flat\"

2. \"This was a long-term single income marriage...The wife worked full-time while the husband took on the role of primary caregiver...but the wife also did all the caregiving\"

3. \"The DJ awarded the wife a 40:32.5 split in recognition of her financial contributions...amount of up to...\"

4. \"I find that the DJ had overemphasized the wife’s financial contributions without sufficiently accounting for the husband’s caregiving role\"

5. \"I adjust the ratio to 37.5% in the wife’s favour to reflect a more balanced assessment\"

6. \"This minor adjustment accounts for the husband’s sustained indirect contributions over the course of the marriage\"

7. \"The parties shall have joint custody of the children...\"

"""
        return [template1, template2]
    
    def _get_openai_prompt(self) -> str:
        """
        Get the prompt for OpenAI.
        
        Returns:
            The prompt template
        """
        return (
            "Outputs should always be in a single line, separated by a tab character. You are a paralegal. Only consider the findings of the judge, and NOT the parties' submissions. Based on the following case judgment text, extract the following information:\n"
            "1. Income Type\n"
            "   - Specify 'Single' or 'Dual' income marriage. If the income from any party is not substantial, indicate which party's income was deemed not substantial by the judge in brackets. If not discussed, reply 'Not Discussed'.\n"
            "2. Average Ratio\n"
            "   - the case will have a table that sets out the average and final ratio. If there is no table, output 'NA'.\n"
            "3. Final Ratio\n"
            "   - The final ratio assigned for the division of matrimonial assets between husband and wife, as determined by the appellate court. Provide the wife's ratio as a percentage (e.g., '55'). If not discussed, state 'NA'.\n"
            "4. Adjustments\n"
            "   - Adjustments are a ratio that adds a modification to the average ratio to derive the final ratio. They are typically expressed as Minus 5 / Plus 5.\n"
            "   - If the judge made no adjustments, output '0'. If an adjustment was made, specify 'Minus [number]' or 'Plus [number]'. If not discussed, output 'NA'.\n"
            "FORMAT OF OUTPUT IS ESSENTIAL!!! IT IS ABSOLUTELY CRITICAL that you return the data as a SINGLE line with the values separated by a TAB CHARACTER, in the exact order specified above.\n"
            "For example, follow this output format: Dual\t45\t55\tPlus 10\t"
        )
    
    def _get_extraction_prompt(self) -> str:
        """
        Get the prompt for comparing LLM outputs.
        
        Returns:
            The prompt template
        """
        return (
            "You are a meticulous paralegal tasked with comparing two lists of legal outputs: {output_1} and {output_2}.\n\n"
            "For each pair of corresponding items:\n"
            "- Return False if both items mean the same thing, even if phrased differently.\n"
            "- Return True only if the meanings are actually different (e.g. different facts, numbers, or legal interpretations).\n\n"
            "Treat the following as equivalent: 'NA', 'Undisclosed', '0', or elaborations that don't change meaning.\n\n"
            "Output the result as a plain list of booleans, separated by commas and within square brackets, with no extra text or formatting.\n"
            "For example: [False, False, True, False]\n"
            "Another example: [True, False, True, False]\n"
            "Do not include any explanation, markdown, code blocks, or commentary.\n"
            "Just return the list, nothing else."
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def chunk_text(self, text: str, max_tokens: int = 190000) -> List[str]:
        """
        Chunk large text into smaller parts.
        
        Args:
            text: The text to chunk
            max_tokens: Maximum tokens per chunk
            
        Returns:
            A list of text chunks
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        chunks = [tokens[i:i + max_tokens] for i in range(0, len(tokens), max_tokens)]
        return [encoding.decode(chunk) for chunk in chunks]
    
    def extract_gemini_output(self, prompt: str) -> str:
        """
        Call Gemini with a retry mechanism to extract the required fields.
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            The response from Gemini
        """
        input_tokens = self.count_tokens(prompt)
        max_completion_tokens = min(self.token_limit - input_tokens - 100, 500000)
        if max_completion_tokens < 1000:
            return "Error: Input too large."
        
        max_retries = 5
        wait_time = 60  # seconds between retries
        attempt = 0
        
        while attempt < max_retries:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-pro-exp-03-25",
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        max_output_tokens=max_completion_tokens,
                        temperature=0.0
                    ),
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Error during Gemini API call: {e}. Retrying in {wait_time} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                attempt += 1
        return f"Error: Failed after {max_retries} attempts."
    
    def extract_gemini_case_output(self, prompt_template: str, case_title: str, case_details: str) -> str:
        """
        Extract information from a case using Gemini.
        
        Args:
            prompt_template: The prompt template to use
            case_title: The title of the case
            case_details: The details of the case
            
        Returns:
            The response from Gemini
        """
        prompt = f"Extract the required legal data from {case_title}:\n\n{case_details}"
        full_prompt = prompt_template.replace("{content}", prompt)
        return self.extract_gemini_output(full_prompt)
    
    def process_gemini_output(self, case_title: str, output: str) -> Tuple[str, str]:
        """
        Process the output from Gemini.
        
        Args:
            case_title: The title of the case
            output: The output from Gemini
            
        Returns:
            A tuple of (answers, evidence)
        """
        if "|||ANSWERS|||" in output and "|||EVIDENCE|||" in output:
            try:
                # Split the result based on the markers
                answer_and_evidence = output.split("|||ANSWERS|||", 1)[1]  # everything after "answers" marker
                answers, evidence = answer_and_evidence.split("|||EVIDENCE|||", 1)
                answers = answers.strip()
                evidence = evidence.strip()
            except Exception as e:
                logger.error(f"Error processing {case_title} with markers: {str(e)}")
                answers = "Error\tError\tError\tError\tError\tError"
                evidence = "Error processing output"
        else:
            # Fallback to splitting using double newline if markers are absent.
            parts = output.split("\n\n", 1)
            answers = parts[0].strip()
            evidence = parts[1].strip() if len(parts) > 1 else "No supporting text returned."

        return answers, evidence
    
    def extract_openai_output(self, instructions: str, case_name: str, case_details: str) -> str:
        """
        Extract information from a case using OpenAI.
        
        Args:
            instructions: The instructions to send to OpenAI
            case_name: The name of the case
            case_details: The details of the case
            
        Returns:
            The response from OpenAI
        """
        max_retries = 3
        wait_time = 60  # seconds
        attempt = 0

        input_text = f"Extract the required legal data from {case_name}:\n\n{case_details}"

        while attempt < max_retries:
            try:
                response = self.openai_client.responses.create(
                    model="gpt-4o",
                    instructions=instructions,
                    input=input_text,
                    temperature=0.0
                )
                return response.output_text.strip()
            except Exception as e:
                error_message = str(e).lower()
                logger.error(f"Encountered error with OpenAI: {e}")
                if "rate limit" in error_message:
                    logger.warning(f"Rate limit encountered. Waiting for {wait_time} seconds before retrying... (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    logger.error("Unhandled error encountered. Aborting extraction.")
                    return "Error"
        
        return f"Error: Failed after {max_retries} attempts."
    
    def compare_llm_output(self, output_1: List[str], output_2: List[str]) -> List[bool]:
        """
        Compare outputs from different LLMs.
        
        Args:
            output_1: The first output
            output_2: The second output
            
        Returns:
            A list of booleans indicating whether the outputs differ
        """
        full_prompt = self.extraction_prompt.format(output_1=output_1, output_2=output_2)
        response = self.extract_gemini_output(full_prompt)
        
        try:
            return ast.literal_eval(response)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return [True] * len(output_1)  # fallback: treat all as mismatches
    
    def clean_evidence_line(self, evidence_line: str) -> str:
        """
        Clean an evidence line.
        
        Args:
            evidence_line: The evidence line to clean
            
        Returns:
            The cleaned evidence line
        """
        # Remove leading numbering e.g., "1.\t", "2. ", etc.
        cleaned = re.sub(r'^\s*\d+\.\s*', '', evidence_line)

        # Replace non-breaking space with normal space
        cleaned = cleaned.replace('\xa0', ' ')

        # Remove leading quote if it's at the start
        cleaned = re.sub(r'^[\'"""]', '', cleaned)

        # Remove trailing quote if it's at the end
        cleaned = re.sub(r'[\'"""]$', '', cleaned)

        # Strip leading/trailing whitespace again
        cleaned = cleaned.strip()

        return cleaned
    
    def process_case(self, case_title: str, case_details: str) -> Dict[str, Any]:
        """
        Process a case with both Gemini and OpenAI.
        
        Args:
            case_title: The title of the case
            case_details: The details of the case
            
        Returns:
            A dictionary with the processed results
        """
        all_fields = []
        all_evidence = []
        
        # Process with Gemini
        for idx, prompt_template in enumerate(self.gemini_prompt_templates):
            try:
                result_gemini = self.extract_gemini_case_output(prompt_template, case_title, case_details)
                if result_gemini is None:
                    logger.warning(f"Received None result for {case_title} with prompt {idx+1}")
                    # Fill with placeholder values
                    answers = "\t".join(["NA"] * (6 if idx == 0 else 7))
                    evidence = "NA"
                else:
                    answers, evidence = self.process_gemini_output(case_title, result_gemini)
            except Exception as e:
                logger.error(f"Error processing {case_title} with prompt {idx+1}: {str(e)}")
                # Fill with placeholder values
                answers = "\t".join(["NA"] * (6 if idx == 0 else 7))
                evidence = "NA"

            fields = answers.split("\t")
            evidence_lines = [self.clean_evidence_line(line) for line in evidence.strip().split("\n") if line.strip()]

            all_fields.extend(fields)
            all_evidence.extend(evidence_lines)

            logger.info(f"Processed {case_title} Prompt {idx+1}\nResult: {answers}")
        
        # Ensure we have enough fields for all columns
        while len(all_fields) < 13:  # Fill missing fields
            all_fields.append("NA")
        
        # Process with OpenAI
        try:
            gpt_output = self.extract_openai_output(self.openai_prompt, case_title, case_details)
            if gpt_output is None or not gpt_output.strip():
                gpt_fields = ["NA", "NA", "NA", "NA"]
            else:
                gpt_fields = gpt_output.strip().split("\t")
                # Ensure we have exactly 4 fields
                while len(gpt_fields) < 4:
                    gpt_fields.append("NA")
                if len(gpt_fields) > 4:
                    gpt_fields = gpt_fields[:4]
        except Exception as e:
            logger.error(f"Error extracting GPT fields for {case_title}: {str(e)}")
            gpt_fields = ["NA", "NA", "NA", "NA"]
        
        # Get Gemini fields for comparison
        try:
            field_indices = [5, 8, 9, 10]  # Indices for the fields we want to compare
            gemini_fields = []
            for idx in field_indices:
                if idx < len(all_fields):
                    gemini_fields.append(all_fields[idx].strip().lower())
                else:
                    gemini_fields.append("na")
        except Exception as e:
            logger.error(f"Error extracting Gemini fields for {case_title}: {str(e)}")
            gemini_fields = ["na", "na", "na", "na"]
        
        # Compare outputs
        try:
            differences = self.compare_llm_output(gpt_fields, gemini_fields)
        except Exception as e:
            logger.error(f"Error comparing outputs for {case_title}: {str(e)}")
            differences = [False, False, False, False]
        
        return {
            "all_fields": all_fields,
            "all_evidence": all_evidence,
            "gpt_fields": gpt_fields,
            "gemini_fields": gemini_fields,
            "differences": differences
        }
