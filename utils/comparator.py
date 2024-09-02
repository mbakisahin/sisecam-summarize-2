import os
import re
import smtplib
from email.message import EmailMessage

from utils.system_messages import SYSTEM_MESSAGE_COMPARISON
import config
import openai
from tabulate import tabulate
from utils.openAI import OpenAIClient
from utils.send_email import EmailClient


class SummaryComparator:
    """
    A class responsible for comparing summaries using OpenAI's ChatCompletion API
    and sending the comparison results via email.
    """

    def __init__(self, engine="gpt-4o"):
        """
        Initializes the SummaryComparator with the specified OpenAI engine.

        :param engine: The OpenAI model engine to use for comparisons (default: "gpt-4o").
        """
        self.engine = engine
        self.openai_client = OpenAIClient(self.engine)
        self.email_client = EmailClient()

    def compare_with_multiple_neighbors(self, original_file_name, original_summary, neighbors):
        """
        Compares the original summary with multiple neighbor summaries and aggregates the results into a single table.

        :param original_file_name: The file name for the original PDF.
        :param original_summary: A dictionary containing 'summary' and 'pdf_name' for the original PDF.
        :param neighbors: A list of dictionaries where each dictionary contains 'summary' and 'file_path' for a neighbor PDF.
        :return: None
        """
        all_sections = {}

        for i, neighbor in enumerate(neighbors, start=1):
            neighbor_file_name = neighbor['file_path']
            neighbor_summary = neighbor['summary']

            config.app_logger.info(f"Comparing summary {i} from file {neighbor_file_name}.")

            # Compare and accumulate results
            comparison_sections = self.compare_summaries(
                original_file_name=original_file_name,
                original_summary=original_summary,
                neighbor_file_name=neighbor_file_name,
                neighbor_summary=neighbor_summary,
                accumulate=True  # Pass an argument to accumulate results
            )

            # Merge comparison sections with all sections
            for section, content in comparison_sections.items():
                if section not in all_sections:
                    all_sections[section] = {'Original Summary': content['Original Summary'], 'Neighbors': []}
                all_sections[section]['Neighbors'].append((neighbor_file_name, content['Neighbor Summary']))

        # Generate a single HTML table for all comparisons
        table_html = self.generate_html(original_file_name, all_sections)
        subject = f"Summary Comparison Results for {original_file_name} with Multiple Neighbors"
        self.email_client.send_email(subject, table_html, is_html=True)

    def compare_summaries(self, original_file_name, original_summary, neighbor_file_name, neighbor_summary, accumulate=False):
        """
        Compares the original summary with a single neighbor summary using OpenAI in a single comparison.
        Includes the name of the neighbor PDF in the comparison for better context.

        :param original_file_name: The file name for the original PDF.
        :param original_summary: A dictionary containing 'summary' and 'pdf_name' for the original PDF.
        :param neighbor_file_name: The file name for the neighbor PDF.
        :param neighbor_summary: A dictionary containing 'summary' and 'pdf_name' for the nearest neighbor PDF.
        :param accumulate: Boolean flag to determine whether to return sections for aggregation.
        :return: The combined differences between the original summary and the neighbor summary, including PDF names.
        """

        input_text = (
            f"Original Summary:\n{original_summary}\n\n"
            f"Neighbor Summary:\n{neighbor_summary}\n\n"
            f"Please provide the key differences between the original summary and the neighbor summary."
        )

        comparison_result = self.openai_client.compare_texts(input_text, SYSTEM_MESSAGE_COMPARISON)

        sections = self.parse_comparison_result(comparison_result)

        if accumulate:
            return sections

        # # If not accumulating, generate and send the table immediately
        # table_html = self.generate_html(original_file_name, {neighbor_file_name: sections})
        # subject = f"Summary Comparison Results for {original_file_name} vs {neighbor_file_name}"
        # self.email_client.send_email(subject, table_html, is_html=True)

    def parse_comparison_result(self, comparison_result):
        """
        Parses the comparison result into sections.

        :param comparison_result: The raw comparison result from OpenAI.
        :return: A dictionary of sections with original and neighbor summaries.
        """
        sections = {}
        current_section = None
        current_subsection = None

        # Define the list of known section headings
        known_headings = [
            "Identify Core Ideas",
            "Highlight Differences in Content",
            "Assess Tone and Emphasis",
            "Contextual Integrity",
            "Summarize Key Differences"
        ]

        for row in comparison_result.split("\n"):
            row = row.strip()

            # Check if the row contains any known heading
            for heading in known_headings:
                if heading in row:
                    current_section = heading
                    sections[current_section] = {"Original Summary": "", "Neighbor Summary": ""}
                    break  # Stop checking other headings once a match is found

            if "Original Summary" in row:
                current_subsection = "Original Summary"
            elif "Neighbor Summary" in row:
                current_subsection = "Neighbor Summary"
            elif row.startswith("-") and current_section and current_subsection:
                sections[current_section][current_subsection] += row + "<br>"

        return sections

    def generate_html(self, original_file_name, all_sections):
        """
        Creates a single HTML table combining all neighbor comparisons with the original summary.

        :param original_file_name: The name of the original file.
        :param all_sections: A dictionary containing the parsed sections with all neighbor comparisons.
        :return: The HTML string for the combined table.
        """
        # Başlık satırı oluşturma
        table_html = "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        table_html += "<thead><tr>"
        table_html += f"<th style='text-align: left;'>Comparison Category</th>"
        table_html += f"<th style='text-align: left;'>Original Summary ({original_file_name})</th>"

        # Her bir komşu özet için başlık ekleme
        neighbor_files = [neighbor[0] for neighbor in all_sections[list(all_sections.keys())[0]]['Neighbors']]
        for i, neighbor_file in enumerate(neighbor_files, start=1):
            table_html += f"<th style='text-align: left;'>Neighbor Summary {i} ({neighbor_file})</th>"

        table_html += "</tr></thead><tbody>"

        # Her bölüm (section) için tablo satırları oluşturma
        for section, content in all_sections.items():
            table_html += f"<tr>"
            table_html += f"<td style='text-align: left; border-right: 2px solid black;'><strong>{section}</strong></td>"
            table_html += f"<td style='text-align: left; border-right: 2px solid black;'>{content['Original Summary']}</td>"

            for neighbor_file, neighbor_summary in content['Neighbors']:
                table_html += f"<td style='text-align: left;'>{neighbor_summary}</td>"

            table_html += f"</tr>"

        table_html += "</tbody></table>"
        return table_html

