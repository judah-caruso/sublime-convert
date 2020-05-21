# Sublime Convert

A small utility to convert .tmTheme files into .sublime-color-scheme files.

# Usage

Tested on Python 3.6.8

```Bash
python sublime-convert.py [.tmTheme file] [output file]
```

**NOTE**: Sublime Convert only expects VALID .tmTheme files as it does NOT do much *(if any)* syntax error handling or checking. If the theme you're trying to convert already works in Sublime Text, it should convert properly so long as the file isn't missing any common pairs *(&lt;key&gt;/&lt;string&gt;, &lt;key&gt;/&lt;dict&gt;, etc.)* that Sublime Text would normally ignore.

To see an example conversion, look at `Fresh.tmTheme` and `Fresher.sublime-color-scheme`
