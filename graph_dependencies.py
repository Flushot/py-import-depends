#!/usr/bin/env python
from __future__ import with_statement

import os
import re
import ast
from pprint import pprint

import networkx as nx
import argparse


class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.modules = []

    # import x (as y), ...
    def visit_Import(self, node):
        self.modules.extend(map(lambda alias: alias.name, node.names))

    # from x import y, ...
    def visit_ImportFrom(self, node):
        #pprint(node.module)
        if node.module is None:
            # from . import x, ...
            self.modules.extend(map(lambda alias: alias.name, node.names))
        else:
            # from x import y, ...
            self.modules.append(node.module)

    # __import__(x)
    # def visit_Call(self, node):
    #     # TODO: Determine function name from call expression
    #     print node.func
    #     #pprint(node)


def parseDependencies(startPath, recursive):
    importEdges = set()
    modulePat = re.compile(r'/(?P<name>.+?)\.py$')

    for filePath in walkPath(startPath, recursive, 
                             ignoreRegex=r'(/lib/python\d+?\.\d+?/|/\.venv/)'):
        # Only want Python scripts
        moduleMatcher = modulePat.search(filePath)
        if not moduleMatcher:
            continue

        # Module naming ghettoness
        moduleName = moduleMatcher.group('name').replace('/', '.')
        if moduleName.endswith('.__init__'):
            moduleName, _ = moduleName.rsplit('.', 1)

        # Parse module contents
        print 'Parsing "%s" module: %s' % (moduleName, filePath)
        with open(filePath, 'rb') as scriptFile:
            rootNode = ast.parse(scriptFile.read(), filePath)
            visitor = ImportVisitor()
            visitor.visit(rootNode)
            for referencedModule in filter(lambda module: module != '__future__', visitor.modules):
                # Append to adjacency list
                importEdges.add((moduleName, referencedModule))

    return importEdges


def walkPath(startPath, recursive, 
             matchRegex=r'.*', ignoreRegex=None):
    if os.path.isdir(startPath):
        # Path is a directory
        matchPat = re.compile(matchRegex)
        ignorePat = re.compile(ignoreRegex) if ignoreRegex else None

        for dirEntry in os.listdir(startPath):
            filePath = os.path.join(startPath, dirEntry)
            if os.path.isdir(filePath):
                # Recurse into subdirectories
                if recursive:
                    walkPath(filePath, recursive, matchRegex, ignoreRegex)
            elif matchPat.search(filePath) and (ignorePat and not ignorePat.search(filePath)):
                yield filePath
    else:
        # Path is a file
        yield startPath


def createGraph(adjacencyList):
    graph = nx.Graph()
    addedNodes = set()

    def addNode(nodeName):
        if nodeName not in addedNodes:
            graph.add_node(nodeName)
        graph.node[nodeName]['label'] = nodeName
        return nodeName

    for sourceModule, importedModule in adjacencyList:
        graph.add_edge(addNode(sourceModule), 
                       addNode(importedModule))

    return graph


def main():
    argp = argparse.ArgumentParser(description='Builds import dependency graph of Python source')
    argp.add_argument('--input', '-i', required=True, help='Directory to scan Python files')
    argp.add_argument('--recurse', '-r', required=True, action='store_true', help='Recurse into subdirectories?')
    argp.add_argument('--output', '-o', required=True, help='Output GraphML file (*.graphml)')
    args = argp.parse_args()

    dependencyGraph = createGraph(parseDependencies(args.input, recursive=args.recurse))
    nx.write_graphml(dependencyGraph, args.output, prettyprint=True)


if __name__ == '__main__':
    main()
