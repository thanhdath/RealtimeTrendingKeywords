import re
from underthesea import pos_tag as pos_tag_underthesea
from underthesea import sent_tokenize
from collections import Counter

VNUPPER = "A-ZẮẰẲẴẶĂẤẦẨẪẬÂÁÀÃẢẠĐẾỀỂỄỆÊÉÈẺẼẸÍÌỈĨỊỐỒỔỖỘÔỚỜỞỠỢƠÓÒÕỎỌỨỪỬỮỰƯÚÙỦŨỤÝỲỶỸỴ"
VNLOWER = "a-zắằẳẵặăấầẩẫậâáàãảạđếềểễệêéèẻẽẹíìỉĩịốồổỗộôớờởỡợơóòỏõọứừửữựưúùủũụýỳỷỹỵ"

stopwords = open("data/vietnamese-stopwords.txt", encoding="utf8").read().split("\n")
stopwords = [x.strip() for x in stopwords]
stopwords = {x: True for x in stopwords}

def clean_str(text):
    def is_uppercase_sentence(text):
        words = text.split()
        if len(words) < 2:
            return False
        return not any([x.islower() for x in text])
    # text = re.sub(f"#[{VNUPPER}{VNLOWER}0-9_]+", "", text
    # find tag and replace
    # replace \n+ by ". "
    text = re.sub("\n+", ". ", text) 
    text = re.sub("\s+", " ", text)
    # 
    match = re.search(f"#[{VNUPPER}{VNLOWER}0-9_]+", text)
    while match is not None:
        text = text[:match.start()] + ". " + match.group()[1:] + ". " + text[match.end():]
        match = re.search(f"#[{VNUPPER}{VNLOWER}0-9_]+", text)

    text = re.sub(r'https?:\/\/.+[\s]+', '', text)
    text = re.sub(f"[^{VNUPPER}{VNLOWER}0-9 \-\.\?\!\"\'%\(\),:/]", "", text)
    text = re.sub("\s+", " ", text).strip()
    text = re.sub("!", ".", text) # ! cause error, maybe rarely seen on training data
    
    if len(text) < 2: 
        return text
    # check if a sentence is full of upper case
    if is_uppercase_sentence(text):
        text = text[0].upper() + text[1:].lower()
    return text

def merge_tags(tags):
    # merge all nouns to one
    filter_tags = []
    i = -1
    while i < len(tags) - 1:
        i += 1
        word, tag = tags[i] 
        if "N" in tag:
            merged_word = word
            while i + 1 < len(tags):
                wordj, tagj = tags[i+1]
                if "N" not in tagj:
                    break
                merged_word += f" {wordj}"
                i += 1
            filter_tags.append((merged_word, "N"))
        else:
            filter_tags.append((word, tag))
    return filter_tags

def pos_tag(text):
    tags = pos_tag_underthesea(text)
    return tags
    # return merge_tags(tags)

def split_sentence_to_parts(tags):
    parts = []
    i = 0
    temp_part = []
    while i < len(tags):
        word, tag = tags[i]
        if tag in ["CH"] and len(temp_part) > 0:
            parts.append(temp_part)
            temp_part = []
        else:
            temp_part.append((word, tag))
        i += 1
    return parts

def is_number(word):
    if word.isdigit():
        return True
    if re.match(r'^-?\d+[\.,]\d+', word) is not None:
        return True
    return False

def compute_tf(text):
    all_nouns = get_nouns(text)
    tfs = Counter(all_nouns)
    for k, v in tfs.items():
        tfs[k] = v / (len(all_nouns)+1)
    return tfs

def clean_noun(word):
    word = re.sub(r"\.", "", word)
    word = re.sub("\s+", " ", word).strip()
    return word

def get_nouns(text):
    text = str(text)
    if len(text) == 0 or text == "nan":
        return []
    sentences = sent_tokenize(text)
    words = []
    for sentence in sentences:
        sentence = clean_str(sentence)
        tags = pos_tag(sentence)
        for word, tag in tags: 
            # if word.startswith(".") and len(word) > 1:
            #     import pdb; pdb.set_trace()
            if "N" in tag:
                words.append(word)
    words = [x.lower() for x in words if len(x) > 1]
    # normalize
    words = [clean_noun(word) for word in words]
    return words
    