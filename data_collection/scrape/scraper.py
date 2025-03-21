import os
import re
import logging
import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm
from prompts import SCRAPER_LLM_SYSTEM_PROMPT

class PolicyExtraction(BaseModel):
    """Schema for the OpenAI API response."""
    contains_policy: bool = Field(description="Whether the file contains actual policy text")
    policy_content: str = Field(description="The extracted policy text, with extraneous navigation or non-policy links removed")
    reasoning: str = Field(description="Reasoning behind the decision")

def clean_string(string: str) -> str:
    """Remove unnecessary characters and extra spaces or newlines from a string"""
    return re.sub(r'[^a-zA-Z0-9\s]', '', string)

def scrape_policies(df: pd.DataFrame, api_key: str = None, model: str = None, base_path: str = None, scraped_policies_dir: str = None, logger: logging.Logger = None) -> pd.DataFrame:
    """Process Markdown files to identify and extract policy text.
    
    This function analyzes each Markdown file specified in the DataFrame's file_path
    column using OpenAI's API to determine if it contains actual policy text and 
    extracts the relevant content.
    
    Args:
        df (pandas.DataFrame): DataFrame containing file_path column with paths to Markdown files.
        api_key (str, optional): OpenAI API key. If None, will use OPENAI_API_KEY environment variable.
        model (str, optional): OpenAI model to use for analysis. Defaults to "o3-mini".
        base_path (str, optional): Base path to prepend to file paths in DataFrame.
        scraped_policies_dir (str, optional): Directory to save scraped policies.
        logger (logging.Logger, optional): Logger to use for logging.
        
    Returns:
        pandas.DataFrame: Original DataFrame with added columns:
            - contains_policy: Boolean indicating if the file contains policy text
            - policy_content: Extracted policy text if contains_policy is True
            - extraction_reasoning: Model's explanation for its decision
            
    Raises:
        FileNotFoundError: If any of the specified file paths don't exist.
        ValueError: If the DataFrame doesn't contain a 'file_path' column.
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Create copies of the required columns to avoid modifying the original during iteration
    results = []
    
    # Process each file
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing files"):
        file_path = os.path.join(base_path, row['file_path'])
        
        # Print file being processed
        logger.info(f"\n{'-'*80}")
        logger.info(f"Processing file {index+1}/{len(df)}: {file_path}")
        logger.info(f"{'-'*80}")
        
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Prepare the system message
            system_message = SCRAPER_LLM_SYSTEM_PROMPT
            
            # Call the OpenAI API with structured output
            response = client.beta.chat.completions.parse(
                model=model,
                reasoning_effort="high",  # Using high reasoning effort for thorough analysis
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Analyze the following markdown content:\n\n{content}"}
                ],
                response_format=PolicyExtraction,
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            
            # Check if there was a refusal
            if hasattr(response.choices[0].message, 'refusal') and response.choices[0].message.refusal:
                result = {
                    'contains_policy': False,
                    'policy_content': f"API refused to process: {response.choices[0].message.refusal}",
                    'reasoning': 'API refused to process the content'
                }
            else:
                # Parse the JSON response
                import json
                result = json.loads(response_content)
            
            # Log the results
            logger.info(f"\nRESULTS:")
            logger.info(f"Contains policy: {result['contains_policy']}")
            logger.info(f"Reasoning: {result['reasoning']}")
            if result['contains_policy']:
                policy_content = clean_string(result['policy_content'])
                policy_name = row['url'].split("/")[-1]
                policy_content_path = os.path.join(scraped_policies_dir, policy_name + ".txt")
                result['policy_content_path'] = policy_content_path
                logger.info(f"\nEXTRACTED POLICY SAVED TO: {policy_content_path}")
                logger.info(f"{'-'*40}")
                logger.info(policy_content)
                logger.info(f"{'-'*40}")
                with open(policy_content_path, "w") as f:
                    f.write(policy_content)
            else:
                logger.info("No policy content extracted.")
            
        except Exception as e:
            # Handle exceptions
            result = {
                'contains_policy': False,
                'policy_content': f"Error processing file: {str(e)}",
                'policy_content_path': None,
                'reasoning': f"Exception occurred: {str(e)}"
            }
            
            # Log error
            logger.error(f"\nERROR processing file:")
            logger.error(f"Exception: {str(e)}")
        
        results.append(result)
    
    # Add the results to the DataFrame
    df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
    df['contains_policy'] = [result['contains_policy'] for result in results]
    df['policy_content_path'] = [result['policy_content_path'] for result in results]
    
    # Optionally, you can also add the reasoning column if needed
    df['extraction_reasoning'] = [result['reasoning'] for result in results]
    
    logger.info("\n" + "="*80 + "\n" + "POLICY EXTRACTION COMPLETE" + "\n" + "="*80)
    logger.info(f"Total files processed: {len(df)}")
    logger.info(f"Files containing policies: {sum(df['contains_policy'])}")
    logger.info(f"Files without policies: {len(df) - sum(df['contains_policy'])}")
    
    return df