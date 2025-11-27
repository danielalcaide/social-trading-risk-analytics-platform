"""
eToro Factsheet Data Extractor

This module provides functions to extract various data from eToro factsheet HTML content.
"""

import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup, Tag


def extract_returns_data(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract returns data from eToro factsheet performance cards.
    
    Args:
        soup: BeautifulSoup object containing the parsed HTML
        
    Returns:
        Dictionary containing performance metrics with labels as keys and values as percentages
    """
    returns_data = {}
    
    # Find performance cards with green or red borders
    return_cards = soup.find_all(
        'div',
        class_=lambda class_name: (
            class_name and 
            ('border-green-900' in class_name or 'border-red-900' in class_name) and
            'p-3' in class_name
        )
    )
    
    for card in return_cards:
        label_element = card.find('div', class_='font-bold text-white text-medium')
        value_element = card.find('span', class_=lambda class_name: (
                class_name and 
                'font-semibold' in class_name and 
                ('text-green-600' in class_name or 'text-red-600' in class_name or 'text-gray-600')
            )
        )
        
        if label_element and value_element:
            label = label_element.get_text(strip=True)
            value = value_element.get_text(strip=True)
            returns_data[label] = value
    
    return returns_data


def extract_about_information(soup: BeautifulSoup) -> str:
    """
    Extract 'About' section information from eToro factsheet.
    
    Args:
        soup: BeautifulSoup object containing the parsed HTML
        
    Returns:
        String containing the about information, empty string if not found
    """
    about_headers = soup.find_all('h2', string=lambda text: text and 'About' in text)
    
    for header in about_headers:
        card = header.find_parent('div', class_=lambda x: x and 'border-slate-700' in x)
        if card:
            content_div = card.find('div', class_='p-4')
            if content_div:
                about_text = content_div.get_text(separator=' ', strip=True)
                # Clean up extra whitespace
                about_text = re.sub(r'\s+', ' ', about_text)
                return about_text
    
    return ""


def extract_popular_investor_stats(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract Popular Investor statistics from eToro factsheet.
    
    Args:
        soup: BeautifulSoup object containing the parsed HTML
        
    Returns:
        Dictionary containing popular investor stats with section names as keys
    """
    stats = {}
    
    # Find all div elements to search for popular investor stats
    div_elements = soup.find_all('div')
    
    for div in div_elements:
        header = div.find('header')
        if header:
            h2_element = header.find('h2')
            if h2_element:
                label_element = div.find('span', class_="text-5xl")
                if label_element:
                    section_name = h2_element.get_text(strip=True)
                    stat_value = label_element.get_text(strip=True)
                    stats[section_name] = stat_value
    
    return stats


def extract_portfolio_breakdowns(soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract sectors, exchanges, and countries breakdowns from portfolio HTML
    
    Args:
        soup: BeautifulSoup object containing the parsed HTML
        
    Returns:
        Dictionary containing breakdowns for sectors, exchanges, and countries
    """
    breakdowns = {
        'sectors': [],
        'exchanges': [],
        'countries': []
    }
    
    # Find the Diversification section
    diversification_header = soup.find('h2', string='Diversification')
    if not diversification_header:
        return breakdowns
    
    diversification_container = diversification_header.find_parent('div')
    if not diversification_container:
        return breakdowns
    
    headers = diversification_container.find_all('h2', class_='font-semibold text-slate-100')
    
    for header in headers:
        section_title = header.get_text().strip()
        
        # Find the parent card container
        card = header.find_parent('div', class_=lambda x: x and 'border-2' in x)
        if not card:
            continue
            
        # Find the list items within this card
        list_items = card.find_all('li', class_='relative px-2 py-1 cursor-pointer hover:bg-slate-900')
        
        section_data = []
        
        for item in list_items:
            name = ""
            percentage = ""
            
            # Extract the name/label
            name_elem = item.find('div', class_='font-semibold')
            if name_elem:
                # Get text content, handling both emoji + text combinations
                name = name_elem.get_text(strip=True)
            else:
                name_elem = item.find('span', class_='font-semibold')
                if name_elem:
                    name = name_elem.find_parent('div').text.strip()

            # Extract the percentage from the font-medium div
            percentage_elem = item.find('div', class_='font-medium')
            if percentage_elem:
                percentage = percentage_elem.get_text().strip()
            
            if name and percentage:
                section_data.append({
                    'name': name,
                    'percentage': percentage
                })
        
        # Categorize based on section title
        if 'Sectors' in section_title:
            breakdowns['sectors'] = section_data
        elif 'Exchanges' in section_title:
            breakdowns['exchanges'] = section_data
        elif 'Countries' in section_title:
            breakdowns['countries'] = section_data
    
    return breakdowns


def extract_all_factsheet_data(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Unified function to extract all available data from factsheet.
    
    Args:
        soup: BeautifulSoup object containing the parsed HTML
        
    Returns:
        Dictionary containing all extracted data:
        - returns: Performance metrics
        - about: About section text
        - popular_investor_stats: Popular investor statistics
        - portfolio_breakdowns: Sectors, exchanges, and countries breakdowns
    """
    return {
        'returns': extract_returns_data(soup),
        'about': extract_about_information(soup),
        'popular_investor_stats': extract_popular_investor_stats(soup),
        'portfolio_breakdowns': extract_portfolio_breakdowns(soup)
    }