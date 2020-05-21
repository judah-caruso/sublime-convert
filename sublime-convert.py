"""
    sublime-convert - A tmTheme to Sublime Color Scheme converter

    This is a small Python utility to convert .tmTheme
    files into .sublime-color-scheme files. This means
    the tool  is essentially a specialized XML to JSON
    converter. It expects  VALID  .tmTheme files as it
    does NOT do much (if any) syntax error handling or
    checking. If  the  theme  you're trying to convert
    already works in Sublime Text, it  should  convert
    properly so  long  as  the  file isn't missing any
    common pairs (<key>/<string>,  <key>/<dict>, etc.)
    that Sublime Text would normally ignore.

    Tested on Python 3.6.8

    USAGE:
        python sublime-converter.py [.tmTheme file] [output file]


    License: MIT

    Copyright (c) 2020 Judah Caruso (0px.moe)

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
"""

from json import dumps
from sys  import argv, stderr
from xml.etree.ElementTree import fromstring


def error(str):
    print(f"Error: {str}", file=stderr) # sys.stderr
    exit(1)


def parse_theme_info(theme):
    theme_info = {}

    for dct in theme:
        keys   = dct.findall("key")
        values = dct.findall("string")

        if len(keys) > 0:
            keys = [key for key in keys if key.text != "settings"]
            keys = format_keys(keys)

        # Remove UUID
        for i in range(len(keys) - 1):
            if keys[i].text == "uuid":
                keys.pop(i)
                values.pop(i)

        parse_dict(theme_info, keys, values)

    return theme_info


def parse_dict(map, keys, values, is_color=False, color_palette=None):
    color = None

    for key in keys:
        for value in values:
            if value.text != None:
                if is_color and color_palette != None:
                    color = get_color_id(value.text, color_palette)

                if color != None:
                    map[key.text] = f"var({color})"
                else:
                    map[key.text] = value.text.strip()

            values.remove(value)
            break

    if len(values) > 0:
        map[keys[len(keys) - 1].text] = values[len(values) - 1].text


def format_keys(keys):
    for key in keys:
        formatted_key = ''.join([f"_{c.lower()}" if c.isupper() else c for c in key.text])
        key.text      = formatted_key

    return keys


def parse_global_values(theme, color_palette):
    global_values = {}

    for root in theme:
        for array in root.findall("array"):
            for dct in array:
                if dct[0].text == "settings":
                    if len(dct) < 2: continue

                    keys = dct[1].findall("key")

                    if len(keys) > 0:
                        keys = format_keys(keys)

                    values = dct[1].findall("string")

                    parse_dict(global_values, keys, values)
                    array.remove(dct)

    for key, value in global_values.items():
        for id, color in color_palette.items():
            if value == color:
                global_values[key] = f"var({id})"

    return global_values


def parse_colors(theme):
    if len(theme) <= 0: return

    colors    = []
    color_map = {}

    # Yikes...
    for array in theme[0].findall("array"):
        for dct in array:
            for value in dct:
                if value.tag == "dict":
                    for color in value:
                        if color.text != None and color.text.startswith("#"):
                            if not color.text in colors:
                                colors.append(color.text)

    for i in range(len(colors)):
        color = colors[i]
        color_map[f"color{i:02d}"] = color

    return color_map


def get_color_id(value, color_palette):
    for id, color in color_palette.items():
        if value == color:
            return id


def parse_rules(theme, color_palette):
    rules = []

    for root in theme:
        for array in root.findall("array"):
            for dct in array:
                keys     = dct.findall("key")
                values   = dct.findall("string")
                rule_map = {}

                if keys[len(keys) - 1].text == "settings":
                    keys.pop()

                parse_dict(rule_map, keys, values)

                for setting in dct.findall("dict"):
                    keys = setting.findall("key")

                    if len(keys) > 0:
                        keys = format_keys(keys)

                    values = setting.findall("string")
                    parse_dict(rule_map, keys, values, True, color_palette)

                rules.append(rule_map)

    return rules


def make_theme(info, global_values, color_palette, rules):
    formatted_map = {}
    formatted_map.update(info)
    formatted_map.update({"variables": color_palette})
    formatted_map.update({"globals": global_values})
    formatted_map.update({"rules": rules})

    json_string = dumps(formatted_map, indent=4) # json.dumps

    return json_string


def generate_header():
    return """/*
 * This theme was auto generated!
 *
 * Parts of this theme may differ
 * from the original, and color
 * definitions using 'alpha'
 * might not convert properly.
 *
 * Tool created by Judah Caruso
 * https://github.com/kyoto-shift
 *
 * License: MIT
*/\n"""


def main(args):
    if len(args) < 3:
        print(f"Usage: {argv[0]} [input] [output]")
        exit(0)

    input_file  = args[1]
    output_file = args[2]

    if not input_file.lower().endswith('.tmtheme'):
        filename = input_file.split('.')
        error(f"Expected a 'tmtheme' file, was given '{filename[len(filename) - 1]}'")

    if not output_file.lower().endswith('.sublime-color-scheme'):
        output_file += '.sublime-color-scheme'

    try:
        with open(input_file, "r") as fh:
            theme_file = fh.read()

        parsed = fromstring(theme_file) # xml.etree.ElementTree.fromstring
    except:
        error(f"Unable to parse file '{input_file}'! Is it valid?")

    theme_info      = parse_theme_info(parsed)
    color_palette   = parse_colors(parsed)
    global_values   = parse_global_values(parsed, color_palette)
    rules           = parse_rules(parsed, color_palette)
    converted_theme = make_theme(theme_info, global_values, color_palette, rules)

    try:
        with open(output_file, "w+") as fh:
            fh.write(generate_header())
            fh.write(converted_theme)
    except:
        error(f"Unable to create file '{output_file}'! Do you have the right permissions?")

    print(f"Successfully converted '{input_file}' to '{output_file}'")


if __name__ == "__main__":
    main(argv) # sys.argv
