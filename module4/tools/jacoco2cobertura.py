#!/usr/bin/env python3
"""Convert a JaCoCo XML report to Cobertura XML so the Jenkins Cobertura plugin can read it.

The classic cobertura-maven-plugin does not run on Java 17+ class files, so JaCoCo
produces the coverage data and this script rewrites it in Cobertura's format.

Usage: jacoco2cobertura.py <jacoco.xml> <coverage.xml>
"""
import sys
import xml.etree.ElementTree as ET


def counter(node, kind):
    """Return (missed, covered) for the given counter type, or (0, 0) if absent."""
    for c in node.findall("counter"):
        if c.get("type") == kind:
            return int(c.get("missed")), int(c.get("covered"))
    return 0, 0


def rate(covered, total):
    return round(covered / total, 4) if total else 0.0


def convert(jacoco_path, cobertura_path):
    report = ET.parse(jacoco_path).getroot()

    line_missed, line_covered = counter(report, "LINE")
    branch_missed, branch_covered = counter(report, "BRANCH")

    coverage = ET.Element("coverage", {
        "line-rate": str(rate(line_covered, line_covered + line_missed)),
        "branch-rate": str(rate(branch_covered, branch_covered + branch_missed)),
        "lines-valid": str(line_covered + line_missed),
        "lines-covered": str(line_covered),
        "branches-valid": str(branch_covered + branch_missed),
        "branches-covered": str(branch_covered),
        "version": "jacoco2cobertura",
        "timestamp": "0",
    })
    sources = ET.SubElement(coverage, "sources")
    ET.SubElement(sources, "source").text = "src/main/java"
    packages_el = ET.SubElement(coverage, "packages")

    for package in report.findall("package"):
        pkg_name = package.get("name", "").replace("/", ".")
        pkg_el = ET.SubElement(packages_el, "package", {"name": pkg_name})
        classes_el = ET.SubElement(pkg_el, "classes")

        for cls in package.findall("class"):
            cls_name = cls.get("name", "").replace("/", ".")
            src_file = cls.get("sourcefilename", "")
            src_pkg_path = package.get("name", "")
            filename = f"{src_pkg_path}/{src_file}" if src_pkg_path else src_file

            # Each JaCoCo <class> maps to a Cobertura <class>; lines come from the
            # matching <sourcefile> node of its package.
            sourcefile = next((s for s in package.findall("sourcefile")
                               if s.get("name") == src_file), None)
            lines_el = ET.Element("lines")
            if sourcefile is not None:
                for line in sourcefile.findall("line"):
                    covered = int(line.get("ci")) > 0
                    ET.SubElement(lines_el, "line", {
                        "number": line.get("nr"),
                        "hits": "1" if covered else "0",
                        "branch": "false",
                    })

            line_missed, line_covered = counter(cls, "LINE")
            branch_missed, branch_covered = counter(cls, "BRANCH")
            class_el = ET.SubElement(classes_el, "class", {
                "name": cls_name,
                "filename": filename,
                "line-rate": str(rate(line_covered, line_covered + line_missed)),
                "branch-rate": str(rate(branch_covered, branch_covered + branch_missed)),
                "complexity": "1",
            })
            ET.SubElement(class_el, "methods")
            class_el.append(lines_el)

        pkg_el.set("line-rate", coverage.get("line-rate"))
        pkg_el.set("branch-rate", coverage.get("branch-rate"))
        pkg_el.set("complexity", "1")

    ET.ElementTree(coverage).write(cobertura_path, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convert(sys.argv[1], sys.argv[2])
