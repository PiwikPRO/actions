import os
import sys
import glob


assert (
    len(sys.argv) == 2
), "Pass a single argument, that is a path to directory where index.html should be created"

directory_to_create_index_of = sys.argv[1]

if not os.path.exists(directory_to_create_index_of):
    print("The requested directory does not exists - skipping generation of index.html")
    sys.exit(0)

index_html_path = os.path.join(directory_to_create_index_of, "index.html")

if os.path.isfile(index_html_path):
    sys.exit(0)

files_to_be_included_in_the_list = set()
for file in glob.glob(directory_to_create_index_of + "/**/**", recursive=True):
    if os.path.isdir(file):
        continue
    files_to_be_included_in_the_list.add(
        os.path.relpath(os.path.abspath(file), os.path.abspath(directory_to_create_index_of))
    )

index_html_content = (
    "<h3>Index of artifacts:</h3>"
    "<hr/>"
    "<ul>"
    + "".join(
        [
            f'<a href="{f}"><li>{f}</li></a>\n'
            for f in files_to_be_included_in_the_list
            if f != "index.html"
        ]
    )
    + "</ul>"
)

with open(index_html_path, "w") as f:
    f.write(index_html_content)
