import re

# Define the event descriptions and corresponding categories with multiple keywords
categories = {
    1: ["goes home", "returns home", "arrives home"],
    2: ["leaves home", "exits home", "departs home"],
    3: ["visitors arrive", "guests arrive"],
    4: ["go up stairs", "go down stairs", "walk past stairs"],
    5: ["plays with pets", "interacts with pets"],
    6: ["fighting", "fight", "brawl"],
    7: ["eating a meal", "eat meal", "having meal", "dining"],
    8: ["watering plants", "water plants"],
    9: ["making a phone call", "playing the piano", "playing the guitar", "playing drums", "reading", "books", "horseback riding", "riding a bike", "running", "walking", "jumping", "sleeping", "taking a photo", "using the computer"],
    10: ["dogs barking", "cats meowing"],
    11: ["dog runs out the door", "cat runs out the door"],
    12: ["dog jumps on the couch", "cat jumps on the couch"],
    13: ["dog causes mischief", "cat causes mischief"],
    14: ["car comes home", "car leaves home"],
    15: ["car parks in the garage"],
    16: ["car horn honking", "honks horn"],
    17: ["car passes by", "fire truck", "ambulance", "truck", "police car"],
    18: ["approaches the car", "stealing the car"],
    19: ["door opens"],
    20: ["door closes"],
    21: ["package delivery", "delivers package"],
    22: ["garbage collection", "collects garbage"],
    23: ["falling", "falls down"],
    24: ["getting off the bed", "gets off bed"],
    25: ["arrives at a location", "arrives at place"],
    26: ["leaves a location", "leaves place"],
    27: ["people passing by", "passes by"],
    28: ["interacting with objects", "uses object"],
    29: ["conversations", "talking", "speaking"],
    30: ["vehicles parked", "car parked"]
}

def categorize_description(description):
    description_lower = description.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower):
                return category, keyword
    return None, None

def process_file(input_file, output_file):
    with open(input_file, 'r') as file:
        content = file.read()

    entries = content.split('\n\n')
    positive_descriptions = []

    for entry in entries:
        if 'Final Description: positive' in entry:
            match = re.search(r'Description: (.*?)(?:Final Description:)', entry, re.DOTALL)
            if match:
                description = match.group(1).strip()
                category, keyword = categorize_description(description)
                if category:
                    positive_descriptions.append(f"Category {category}: {keyword}\n{entry}")

    filtered_content = '\n\n'.join(positive_descriptions)

    with open(output_file, 'w') as output_file:
        output_file.write(filtered_content)

if __name__ == "__main__":
    input_file = 'video_descriptions.txt'
    output_file = 'filtered_descriptions.txt'
    process_file(input_file, output_file)
    print(f"Filtered descriptions have been written to {output_file}")
