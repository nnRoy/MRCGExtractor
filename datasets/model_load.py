from openai import OpenAI
import json
from transformers import AutoTokenizer
import time
import tiktoken

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
from accelerate import infer_auto_device_map, dispatch_model

import os
import config as config


class GPTClient:
    def __init__(self, model):
        self.client = OpenAI(api_key=config.GPT_API_KEY)
        self.model = model
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def static_tokens(self, prompt):
        return len(self.encoding.encode(prompt))


    def truncate_messages(self, prompt, max_tokens=120000):
        if len(self.encoding.encode(prompt)) >= max_tokens:
            return self.encoding.decode(self.encoding.encode(prompt)[len(self.encoding.encode(prompt)) - max_tokens:])
        return prompt

    def generate_code_1(self, prompt, max_new_tokens = 512):
        try:
            outputs = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a experienced software engineer."},
                    {"role": "user", "content": self.truncate_messages(prompt)},
                ],
                max_tokens=max_new_tokens,
                temperature=0
            )
            print(outputs.choices[0].message.content + "\n\n\n\n&&&&&&&\n\n\n\n")
            return [outputs.choices[0].message.content]
        except Exception as e:
            print("Error:", e)
            return [""]
    
    def generate_code_n(self, prompt, n=10, temperature=0.6, top_p=0.7, max_new_tokens=512):
        results = []
        for _ in range(n):
            try:
                outputs = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a experienced software engineer."},
                        {"role": "user", "content": self.truncate_messages(prompt)},
                    ],
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p
                )
                print(outputs.choices[0].message.content + "\n\n\n\n&&&&&&&\n\n\n\n")
                results.append(outputs.choices[0].message.content)
            except Exception as e:
                print("Error:", e)
                results.append("")
        return results
    
    def generate_code(self, prompt, n):
        if n == 1:
            return self.generate_code_1(prompt)
        else:
            return self.generate_code_n(prompt, n)
        


class DeepSeekClient:
    def __init__(self, model):
        self.client = OpenAI(api_key=config.DeepSeek_API_KEY, base_url="https://api.deepseek.com")
        self.model = model
        self.tokenizer = AutoTokenizer.from_pretrained("DeepSeek-V3-0324")

    def static_tokens(self, prompt):
        return len(self.tokenizer.encode(prompt))
    
    def truncate_messages(self, prompt, max_tokens=60000):
        if len(self.tokenizer.encode(prompt)) >= max_tokens:
            return self.tokenizer.decode(self.tokenizer.encode(prompt)[len(self.tokenizer.encode(prompt)) - max_tokens:])
        return prompt
    
    def generate_code_1(self, prompt, max_new_tokens=512):
        try:
            outputs = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a experienced software engineer."},
                    {"role": "user", "content": self.truncate_messages(prompt)},
                ],
                stream=False,
                max_tokens=max_new_tokens,
                temperature=0
            )
            print(outputs.choices[0].message.content + "\n\n\n\n&&&&&&&\n\n\n\n")
            return [outputs.choices[0].message.content]
        except Exception as e:
            print("Error:", e)
            return [""]

    def generate_code_n(self, prompt, n=10, temperature=0.6, top_p=0.7, max_new_tokens=512):
        results = []
        for _ in range(n):
            try:
                outputs = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a experienced software engineer."},
                        {"role": "user", "content": self.truncate_messages(prompt)},
                    ],
                    stream=False,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p
                )
                print(outputs.choices[0].message.content + "\n\n\n\n&&&&&&&\n\n\n\n")
                results.append(outputs.choices[0].message.content)
            except Exception as e:
                print("Error:", e)
                results.append("")
        return results
    
    def generate_code(self, prompt, n):
        if n == 1:
            return self.generate_code_1(prompt)
        else:
            return self.generate_code_n(prompt, n)
        

class QwenCoderClient:
    def __init__(self, model_name):
        self.model_path = model_name
        self.model, self.tokenizer = self.load_model()
    
    def load_model(self):
        # model = AutoModelForCausalLM.from_pretrained(
        #     self.model_path,
        #     torch_dtype=torch.float16,
        #     device_map="auto",
        #     load_in_4bit=True
        # )
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            quantization_config=quantization_config,
            trust_remote_code=True
        )
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        return model, tokenizer

    def static_tokens(self, prompt):
        return len(self.tokenizer.encode(prompt))
    
    def get_inputs(self, prompt):
        try:
            messages=[
            {"role": "system", "content": "You are a experienced software engineer."},
            {"role": "user", "content": prompt},
            ],
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            if isinstance(text, list):
                text = text[0]

            model_inputs = self.tokenizer([text], return_tensors="pt", truncation=True, max_length=128000).to(self.model.device)
            return model_inputs
        except Exception as e:
            print(f"Error getting inputs: {e}")
            return None
        
    def generate_code_1(self, prompt, max_new_tokens=512):
        try:
            model_inputs = self.get_inputs(prompt)
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False
            )

            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        
            ]
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            torch.cuda.empty_cache()
            print(response+"\n\n\n\n&&&&&&&\n\n\n\n")
            return [response]
        except Exception as e:
            print(f"Error generating code: {e}")
            return [""]

    def generate_code_n(self, prompt, n=10, temperature=0.6, top_p=0.7, max_new_tokens=512):
        results = []
        model_inputs = self.get_inputs(prompt)
        for _ in range(n):
            try:
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    top_p=top_p
                )

                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        
                ]
                response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                torch.cuda.empty_cache()
                print(response+"\n\n\n\n&&&&&&&\n\n\n\n")
                results.append(response)
            except Exception as e:
                print(f"Error generating code: {e}")
                results.append("")
        return results
    
    def generate_code(self, prompt, n):
        if n == 1:
            return self.generate_code_1(prompt)
        else:
            return self.generate_code_n(prompt, n)
