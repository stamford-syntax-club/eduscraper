import argparse
import json
import re
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://reg.stamford.edu/registrar/"
URL = BASE_URL + "class_info_1.asp?avs517859457=6&backto=student"

PAYLOAD = "facultyid=all&acadyear=2023&semester=1&CAMPUSID=&LEVELID=&coursecode=&coursename=&cmd=2"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://reg.stamford.edu",
    "Referer": "https://reg.stamford.edu/registrar/class_info.asp",
}

COURSES = []


page_counter = 1
start_time = time.time()

def return_milliseconds_elapsed():
    global start_time
    return int((time.time() - start_time) * 1000)


def get_next_page_in_course_list(url_suffix):
    return requests.get(BASE_URL + url_suffix)


# Function to send a POST request to the provided URL,
# but using GET on https://reg.stamford.edu/registrar/class_info_1.asp?facultyid=all&acadyear=2023&semester=1
# Also works... XD
def get_from_reg(url):
    return requests.post(url, headers=HEADERS, data=PAYLOAD)


def parse_page(soup):
    table = soup.findAll("table")[2]
    rows = table.findAll("tr")[2:]

    for row in rows:
        # Remove the first and last td since they"re empty for some reason
        columns = row.findAll("td")[1:-1]
        if columns:
            # Removing some special characters
            data = [column.text.replace(u"\xa0", u" ").strip() for column in columns]
            course = create_course_object(data, columns[1])
            COURSES.append(course)


def create_course_object(data, column):
    course_name, pre_reqs, lecturer_names = parse_column(column)
    return {
        "course_code": data[0],
        "course_name": course_name,
        "credits": data[2],
        "time": data[3],
        "group": data[4],
        "take": data[5],
        "entry": data[6],
        "minimum_seat": data[7],
        "leftover": data[8],
        "status": data[9],
        "study_language": data[10],
        "course_prerequisites": pre_reqs,
        "course_lecturers": lecturer_names,
    }


def parse_column(column):
    course_name = "".join(column.find("font").find_all(string=True, recursive=False)).strip()

    pre_reqs_element = column.find("font", {"color": "#505070"})
    pre_reqs = parse_prerequisites(pre_reqs_element)

    lecturer_names_element = column.find("font", {"color": "#407060"})
    lecturer_names = parse_lecturer_names(lecturer_names_element)

    return course_name, pre_reqs, lecturer_names


def parse_prerequisites(element):
    pre_reqs = []

    if element:
        pre_reqs_text = "".join(element.find_all(string=True, recursive=False))
        pre_reqs_match = re.search(r"\( Pre: (.*)\)", pre_reqs_text)
        if pre_reqs_match:
            pre_reqs = [pre_req.strip() for pre_req in pre_reqs_match.group(1).split("and")]

    return pre_reqs


def parse_lecturer_names(element):
    lecturer_names = []

    if element:
        lecturer_names = ["".join(li.find_all(string=True, recursive=False)) for li in element.find_all("li")]

    return lecturer_names


def scrape_courses(soup):
    global page_counter
    parse_page(soup)

    while True:
        print(f"Scraping course list page {page_counter}...")
        next_button = soup.find("a", string="[NEXT]")

        if next_button is None:
            break

        print("Next page found, scraping...\n")

        next_page = get_next_page_in_course_list(next_button.get("href"))
        soup = BeautifulSoup(next_page.content, "html.parser")
        parse_page(soup)
        page_counter += 1


def main(output_filename):
    response = get_from_reg(URL)
    soup = BeautifulSoup(response.content, "html.parser")

    print("Stamford Scraper v1.0.0 starting...")
    scrape_courses(soup)

    with open(output_filename, "w") as f:
        json.dump(COURSES, f, indent=4)

    print("\n")
    print(f"Successfully scraped {len(COURSES)} courses from {page_counter} pages in {return_milliseconds_elapsed()}ms.")
    print(f"Data has been scraped and written to \"{output_filename}\" successfully.")


if __name__ == "__main__":
    # # For debugging purposes:
    # response = get_from_reg(URL)
    # soup = BeautifulSoup(response.content, "html.parser")
    # parse_page(soup)
    #
    # print("Scraped courses from the first page:")
    # print(f"Successfully scraped {len(COURSES)} courses from {page_counter} page(s) in {return_milliseconds_elapsed()}ms.")
    # for course in COURSES:
    #     print(course)

    parser = argparse.ArgumentParser(description="Stamford University Course Scraper")
    parser.add_argument("-f", "--filename", type=str, required=True, help="Output JSON filename")
    args = parser.parse_args()

    main(args.filename)
