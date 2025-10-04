# Sex Offender Registry Scraper

This project contains scripts to scrape sex offender information from the New Jersey State Police website (icrimewatch.net).

## Files

- `sex_offender_scraper.py` - Basic requests-based scraper (may be blocked by DataDome protection)
- `selenium_scraper.py` - Selenium-based scraper that can bypass anti-bot protection
- `test_scraper.py` - Test script to debug website access issues

## Requirements

Install the required dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Selenium Scraper (Recommended)

The Selenium scraper can bypass DataDome protection and is more reliable:

```bash
python scripts/selenium_scraper.py
```

This will:
1. Open a Chrome browser window
2. Navigate to the search results page
3. Extract all offender information
4. Download offender images
5. Save data to CSV and JSON files
6. Store images in the `sex-offenders/images/` folder

### Basic Scraper

The basic scraper uses requests and may be blocked:

```bash
python scripts/sex_offender_scraper.py
```

## Output

The scraper creates the following structure:

```
sex-offenders/
├── data/
│   ├── offenders.csv
│   └── offenders.json
└── images/
    ├── 2305180.jpg
    ├── 2305181.jpg
    └── ...
```

## Data Fields

The scraper extracts the following information for each offender:

- Basic Info: Name, Address, City, ZIP, Address Type
- Risk Level: Alert level and tier information
- Physical Description: Age, Height, Weight, Race, Eyes, Hair
- Offense Information: Description, conviction date, details
- Images: Mugshot photos (both from list and detail pages)

## Legal Notice

This scraper is for educational and research purposes. Please ensure you comply with:
- Website terms of service
- Local laws and regulations
- Data privacy requirements
- Rate limiting and respectful scraping practices

## Troubleshooting

If you encounter issues:

1. **403 Forbidden errors**: The website uses DataDome protection. Use the Selenium scraper instead.
2. **Chrome driver issues**: The webdriver-manager will automatically download the correct ChromeDriver version.
3. **Slow performance**: Increase the delay between requests in the scraper configuration.
4. **Missing data**: Some fields may not be available for all offenders.

## Customization

You can modify the search URL in the main() function to search different areas or adjust the radius:

```python
search_url = "https://www.icrimewatch.net/results.php?AgencyID=55260&SubmitAddrSearch=1&AddrStreet=YOUR_STREET&AddrCity=YOUR_CITY&AddrState=31&AddrZip=YOUR_ZIP&AddrZipPlus=YOUR_ZIP&whichaddr=home_addr%7Ctemp_addr&excludeIncarcerated=0&radius=5"
```
