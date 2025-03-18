import os
import pandas as pd
from openai import OpenAI
from typing import Dict, Any
from pydantic import BaseModel, Field
from tqdm import tqdm

class PolicyExtraction(BaseModel):
    """Schema for the OpenAI API response."""
    contains_policy: bool = Field(description="Whether the file contains actual policy text")
    policy_content: str = Field(description="The extracted policy text, with extraneous navigation or non-policy links removed")
    reasoning: str = Field(description="Reasoning behind the decision")

def extract_policies(df: pd.DataFrame, api_key: str = None, model: str = "o3-mini", base_path: str = None) -> pd.DataFrame:
    """Process Markdown files to identify and extract policy text.
    
    This function analyzes each Markdown file specified in the DataFrame's file_path
    column using OpenAI's API to determine if it contains actual policy text and 
    extracts the relevant content.
    
    Args:
        df (pandas.DataFrame): DataFrame containing file_path column with paths to Markdown files.
        api_key (str, optional): OpenAI API key. If None, will use OPENAI_API_KEY environment variable.
        model (str, optional): OpenAI model to use for analysis. Defaults to "o3-mini".
        base_path (str, optional): Base path to prepend to file paths in DataFrame.
        
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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create copies of the required columns to avoid modifying the original during iteration
    results = []
    
    # Process each file
    print("\n" + "="*80 + "\n" + "STARTING POLICY EXTRACTION PROCESS" + "\n" + "="*80)
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing files"):
        file_path = os.path.join(base_path, row['file_path'])
        
        # Print file being processed
        print(f"\n{'-'*80}")
        print(f"Processing file {index+1}/{len(df)}: {file_path}")
        print(f"{'-'*80}")
        
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Prepare the system message
            system_message = """
            You are an expert at analyzing medical and healthcare policy documents. 
            You will be given markdown content scraped from the Yale School of Medicine 
            and Department of Radiology intranet. Your task is to:
            
            1. Determine if the content actually contains policy text or just links to policies
            2. If it contains policy text, extract the relevant policy content (you might need to extract multiple excerpts from different sections of the document. Attach all together but with a "---" separator)
            3. Remove extraneous navigation, headers, footers, or non-policy links
            4. Retain links that are an integral part of the policy itself
            
            Return your analysis in the following structured format:
            {
                "contains_policy": boolean,  // true if the content contains actual policy text, false otherwise
                "policy_content": string,    // the extracted policy text, empty if contains_policy is false
                "reasoning": string          // explanation of why you determined this is or isn't a policy document
            }
            """
            
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
            print(f"\nRESULTS:")
            print(f"Contains policy: {result['contains_policy']}")
            print(f"Reasoning: {result['reasoning']}")
            if result['contains_policy']:
                print(f"\nEXTRACTED POLICY:")
                print(f"{'-'*40}")
                print(result['policy_content'])
                print(f"{'-'*40}")
            else:
                print("No policy content extracted.")
            
        except Exception as e:
            # Handle exceptions
            result = {
                'contains_policy': False,
                'policy_content': f"Error processing file: {str(e)}",
                'reasoning': f"Exception occurred: {str(e)}"
            }
            
            # Log error
            print(f"\nERROR processing file:")
            print(f"Exception: {str(e)}")
        
        results.append(result)
    
    # Add the results to the DataFrame
    df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
    df['contains_policy'] = [result['contains_policy'] for result in results]
    df['policy_content'] = [result['policy_content'] if result['contains_policy'] else "" for result in results]
    
    # Optionally, you can also add the reasoning column if needed
    df['extraction_reasoning'] = [result['reasoning'] for result in results]
    
    print("\n" + "="*80 + "\n" + "POLICY EXTRACTION COMPLETE" + "\n" + "="*80)
    print(f"Total files processed: {len(df)}")
    print(f"Files containing policies: {sum(df['contains_policy'])}")
    print(f"Files without policies: {len(df) - sum(df['contains_policy'])}")
    
    return df

# Example usage:
original_df = pd.read_csv("/Users/pouria/Documents/Coding/YDR Policy Scraping/data/crawled_data/policies_data.csv")
df_with_policies = extract_policies(original_df, api_key=os.getenv("OPENAI_API_KEY"), base_path="/Users/pouria/Documents/Coding/YDR Policy Scraping/")
df_with_policies.to_csv("/Users/pouria/Documents/Coding/YDR Policy Scraping/data/crawled_data/labeled_policies_data.csv", index=False)