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


def parse_theme_info(theme):
    """
        Finds any top-level metadata about the theme and properly formats it.
        Also removes the UUID and its value from the final theme, as (AFIAK)
        Sublime Text no longer requires that to be within themes.
    """
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
    """
        Parses sublime-color-scheme dictionaries. Should only be used
        when something like:
            <key>settings</key>
            <dict>...</dict>
        is found.
    """
    color_id  = None
    reference = None

    for key in keys:
        for value in values:
            if value.text != None:
                if is_color and color_palette != None:
                    color_id  = get_color_id(value.text, color_palette)
                    color     = value.text
                    reference = color_palette["references"].get(color)

                if reference  != None:
                    map[key.text] = f"var({reference})"
                elif color_id != None:
                    map[key.text] = f"var({color_id})"
                else:
                    map[key.text] = value.text.strip()

            values.remove(value)
            break

    if len(values) > 0:
        map[keys[len(keys) - 1].text] = values[len(values) - 1].text


def format_keys(keys):
    """
        Converts keys like findHighlightForeground to find_highlight_foreground.
    """
    for key in keys:
        formatted_key = ''.join([f"_{c.lower()}" if c.isupper() else c for c in key.text])
        key.text      = formatted_key

    return keys


def parse_global_values(theme, color_palette):
    """
        Parses the "globals" table, converts tmTheme keys to the proper format,
        and resolves any color references.
    """
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
            if id == "references": continue

            if value[-1] == "^":
                reference = color_palette["references"].get(value)
                if reference != None:
                    global_values[key] = f"var({reference})"
            elif value == color:
                global_values[key] = f"var({id})"

    return global_values


def parse_colors(theme):
    """
        Finds each unique color within a theme, parses it, and resolves any
        references. Used as the "variables" table in the final theme.

        If a color explicitly contains an alpha value (rgb(a)), the hexadecimal
        alpha is converted into a float between 0.0 and 1.0, and the definition
        becomes "color(...)" instead of "#...". If the rgb values of two colors
        are the same but their alpha values are different,  the non-alpha color
        is used as a "root," and the alpha value is included separately. The
        definition then becomes:

            #00ff00   => var(color00)
            #00ff00ff => color(var(color00) alpha(1.0))

        Colors that contain alpha values but have no references become:

            #ff00ff00 => color(#ff00ff alpha(0.0))
    """
    if len(theme) <= 0: return

    colors    = []
    color_map = {}

    # Yikes...
    for array in theme[0].findall("array"):
        for dct in array:
            for entry in dct.findall("dict"):
                for color in entry:
                    if color.text != None and color.text.startswith("#"):
                        if len(color.text) > 7:
                            color.text += "^"

                        if not color.text in colors:
                            colors.append(color.text)

    # Create initial color map: ["colorXX"] = "#001122", ["colorXY"] = "#00112233^" (has alpha)
    for i in range(len(colors)):
        color = colors[i]
        color_map[f"color{i:02d}"] = color

    # Create reference lookup table: ["#00112233^"] = "colorXY"
    references = {}
    for id, color in color_map.items():
        if color[-1] == "^":
            color_hex = color[:-3]
            alpha     = int(color[-3:-1], 16) / 255
            reference = get_color_id(color_hex, color_map)

            if reference != None:
                color_map[id] = f"color(var({reference}) alpha({alpha:.2f}))"
            else:
                color_map[id] = f"color({color_hex} alpha({alpha:.2f}))"

            references[color] = id

    color_map.update({"references": references})
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

                if keys[-1].text == "settings":
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
    formatted_map = info
    formatted_map.update({
        "variables" : color_palette,
        "globals"   : global_values,
        "rules"     : rules
    })

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


def error(str):
    print(f"Error: {str}", file=stderr) # sys.stderr
    exit(1)


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

    color_palette.pop("references")

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
