#!/usr/bin/python
# -*- coding: utf-8 -*-

#########################################
##  Author:         Wandrille Duchemin
##  Modified by:    Simon Penel
##  Created:        24-Jan-2023
##  Last modified:  24-Jan-2023
##
##  Decribes one classe : recPhyloXML_parser
##          which enables the reading of recPhyloXML files
##          to write  ete3 derived objects
##
##  requires : ReconciledTree.py
##             ete3 ( http://etetoolkit.org/ )
##             xml ( in standard library )
##
##  developped for python3.0
##
#########################################

import sys
import ete3
import xml.etree.ElementTree as ET

from ReconciledTree import ReconciledTree, RecEvent, ReconciledTreeList , EVENTTAGCORRESPONDANCE

REVERSE_EVENTTAGCORRESPONDANCE = {v:k for k,v in EVENTTAGCORRESPONDANCE.items()}

##allow reading of old speciationOut tags and redirecting them toward the new branchingOut
REVERSE_EVENTTAGCORRESPONDANCE["speciationOut"] = "bro"
REVERSE_EVENTTAGCORRESPONDANCE["speciationLoss"] = "broL"

OBSOLETE_EVENT_TAGS = ["speciationLoss", "speciationOutLoss", "speciationOut" ] #  will give a warning

def OBSOLETEWARNINGTXT(tag):
    return  "The obsolete tag "+tag+" was observed and this may result in unwanted behaviour. Please use a conversion script such as convertToLossIndependentVersion.py to update your file to a newest verszion of the format."

class recPhyloXML_parser:
    def __init__(self):
        pass


    def parse(self , fileName , obsoleteTagsBehaviour = 1 ):
        """
        Please note that this parser is intentionnaly quite permissive (eg. it will allow any kind of event tags, or properties in those tags)
        , in order to accomodate to changes in the format and eventual adaption of it to special problems.

        Takes:
            - fileName (str) : name of a recPhyloXML file containing a single reconciled gene tree
            - obsoleteTagsBehaviour (int) [default = 1]: Behaviour when an event tag that is in OBSOLETE_EVENT_TAGS is encountered
                                                         0 : ignore
                                                         1 : warning
                                                         2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTreeList) : a set of reconciled trees
        """

        tree = ET.parse(fileName)

        root = tree.getroot()

        TAGtoFUNCTION = { "recPhylo" : self.parse_recPhylo,
                          "recGeneTree" : self.parse_recGeneTree }


        parseFunction  = TAGtoFUNCTION.get( self.tagCorrection(root.tag) , None)


        if parseFunction is None:
            raise Exception("recPhyloXML exception. Problem while parsing the xml file : no recPhylo or recgeneTree tag found at the root of the file.")
            return None

        else:
            obj = parseFunction(root, obsoleteTagsBehaviour)

        if obj is None:
            raise Exception("recPhyloXML exception. Problem while parsing the xml file : no phylogeny or clade found?")



        rootIsRT = (self.tagCorrection(root.tag) == "recGeneTree")


        if rootIsRT: #to be sure to return renconiledTreeList, we convert
            return ReconciledTreeList(recTrees = [ obj ])

        return obj


    def tagCorrection(self, tag):
        """
        Takes:
            - tag (str) : tag with or without the "{***}" prefix

        Returns:
            (str) : the tag without this prefix
        """
        return tag.rpartition("}")[2]

    def isOfTag(self, element, tag):
        """
        Takes:
            - element (Element) : an element from xml.etree.ElementTree
            - tag (str) : a tag to check

        Returns:
            (bool) : True if the element has the desired tag, False otherwise
        """
        if self.tagCorrection(element.tag) != tag:
            return False
        return True


    def parseSimpletextElement(self, element):
        """
        Takes:
            - element (Element) : element containing some text only

        Returns:
            (str) : text contained in the element
        """
        return element.text


    def parse_recPhylo(self, element, obsoleteTagsBehaviour = 1 ):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "recPhylo" tag
            - obsoleteTagsBehaviour (int) [default = 1]: 0 : ignore
                                                     1 : warning
                                                     2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTreeList) : a representation of the different recGeneTrees in the file, with their species tree if it is present
        """
        TAG = "recPhylo"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        children = list(element)

        RTL = ReconciledTreeList()

        for ch in children:
            if self.isOfTag(ch,  "recGeneTree" ) :
                RT = self.parse_recGeneTree(ch, obsoleteTagsBehaviour)
                RTL.append(RT)

            elif self.isOfTag(ch,  "spTree" ):
                #parsing a simple tree
                RTL.setSpTree( self.parse_SpTree(ch) )





        return RTL


    def parse_SpTree(self, element):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "spTree" tag

        Returns:
            None : error
                or
            (ete3.Tree) : the species tree
        """
        TAG = "spTree"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        # children = element.getchildren()
        children = list(element)        
        node = None

        for ch in children:
            if self.isOfTag(ch,  "phylogeny" ) :
                node = self.parse_phylogeny(ch, reconciled = False)
                break

        return node


    def parse_recGeneTree(self, element, obsoleteTagsBehaviour = 1 ):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "recGeneTree" tag
            - obsoleteTagsBehaviour (int) [default = 1]: 0 : ignore
                                                         1 : warning
                                                         2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTree) : the reconciled tree
        """
        TAG = "recGeneTree"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        # children = element.getchildren()
        children = list(element)

        node = None

        for ch in children:
            if self.isOfTag(ch,  "phylogeny" ) :
                node = self.parse_phylogeny(ch, reconciled = True, obsoleteTagsBehaviour=obsoleteTagsBehaviour)
                break

        return node


    def parse_phylogeny(self, element , reconciled = True, obsoleteTagsBehaviour = 1 ):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "phylogeny" tag
            - reconciled (bool) [default = True] : whether the element passed should be considered a ReconciledTree or not
            - obsoleteTagsBehaviour (int) [default = 1]: 0 : ignore
                                                         1 : warning
                                                         2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTree) : the reconciled tree
                or
            (ete3.Tree) : the tree (if reconciled is True)
        """
        TAG = "phylogeny"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        # children = element.getchildren()
        children = list(element)

        node = None

        additionnalInfo = {}

        for ch in children:
            if self.isOfTag(ch ,  "clade"):
                if node is None:
                    node  = self.parse_clade(ch, reconciled, obsoleteTagsBehaviour)
                else:
                    raise Exception("BadTagException. A " + TAG + " element has more than one clade children (only one is expected).")
            else:
                ### treatment for other children
                additionnalInfo[ch.tag] = ch



        if node is None:
            raise Exception("BadTagException. A " + TAG + " element has no clade children (one is expected).")


        ### treatment for keys
        for k,v in element.items():
            additionnalInfo[k] = v

        if len(additionnalInfo) > 0:
            node.add_features( **additionnalInfo )


        return node

    def parse_clade(self, element, reconciled = True, obsoleteTagsBehaviour = 1 ):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "clade" tag
            - reconciled (bool) [default = True] : whether the element passed should be considered a ReconciledTree or not
            - obsoleteTagsBehaviour (int) [default = 1]: 0 : ignore
                                                         1 : warning
                                                         2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTree) : the reconciled tree
        """
        TAG = "clade"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        # children = element.getchildren()
        children = list(element)

        name = None
        childrenNodes = []
        events = []

        additionnalInfo = {}

        for ch in children:
            if self.isOfTag(ch ,  "clade" ):
                childrenNodes.append( self.parse_clade(ch , reconciled, obsoleteTagsBehaviour) )

            elif self.isOfTag(ch ,  "name" ):
                name = self.parseSimpletextElement(ch)

            elif self.isOfTag(ch ,  "eventsRec" ):
                events = self.parse_eventsRec(ch, obsoleteTagsBehaviour)

            else:
                ### treatment for other children
                additionnalInfo[ self.tagCorrection( ch.tag ) ] = ch


        ### treatment for keys
        for k,v in element.items():
            if k != "rooted":
                additionnalInfo[k] = v

        node = None

        if reconciled:
            node = ReconciledTree()
        else:
            node = ete3.Tree()

        node.name = name

        if reconciled:
            is_dupl = False
            is_trans = False
            is_loss = False
            for e in events:
                node.addEvent(e) 
                if e.eventCode == "D":
                    is_dupl = True
                if e.eventCode == "Tb":
                    is_trans = True
                if e.eventCode == "L":
                    is_loss = True

            if is_dupl:
                node.add_features(D="T")
            else :
                node.add_features(D="F")
            if is_trans:
                node.add_features(H="T")
            else :
                node.add_features(H="F")
            if is_loss:
                node.add_features(L="T")
            else :
                node.add_features(L="F")

            node.add_features(S=e.species)


        for ch in childrenNodes:
            node.add_child( ch )

        if len(additionnalInfo) > 0:
            node.add_features( **additionnalInfo )


        return node

    def parse_eventsRec(self, element, obsoleteTagsBehaviour = 1 ):
        """
        *recursive funtion*

        Takes:
            - element (Element) : element with the "eventsRec" tag
            - obsoleteTagsBehaviour (int) [default = 1]: 0 : ignore
                                                         1 : warning
                                                         2 : throw exception

        Returns:
            None : error
                or
            (ReconciledTree) : the reconciled tree
        """
        TAG = "eventsRec"

        if not self.isOfTag(element, TAG):
            raise Exception('BadTagException. The element is of tag ' + element.tag + " instead of " + TAG + "." )

        # children = element.getchildren()
        children = list(element)

        events = []

        for ch in children:

            evtCode = self.tagCorrection( ch.tag )

            if obsoleteTagsBehaviour>0:
                if evtCode in OBSOLETE_EVENT_TAGS:
                    print (OBSOLETEWARNINGTXT(evtCode))

                    if obsoleteTagsBehaviour>1:
                        raise Exception("ERROR. obsolete tag " + evtCode + " encoutered")


            evtCode = REVERSE_EVENTTAGCORRESPONDANCE.get(evtCode, evtCode) ## replace by special code when known tag, otherwise keep as is

            species = None
            speciesTAGs  = ["destinationSpecies" , "speciesLocation"]
            ts = None
            tsTAG = "ts"
            additionnalInfo = {}

            it = ch.items()
            for k,v in it:
                if k in speciesTAGs:
                    species = v
                elif k == tsTAG:
                    ts = int(v)
                else:
                    additionnalInfo[k] = v


            evt = RecEvent(evtCode , species, ts, additionnalInfo)

            events.append(evt)


        return events


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} input_file.recphyloxml')
        sys.exit()

    fileName = sys.argv[1]
    parser = recPhyloXML_parser()

    RTL = parser.parse(fileName)
    n = 1
    for RT in RTL.recTrees:
        print("Writing  gene tree number "+str(n)+": [gene_tree."+str(n)+".nw] ...")
        RT.write(features=[],outfile="gene_tree."+str(n)+".nw")
        n = n + 1
        print()

    print("Writing  species tree [species_tree.nw] ...")  
    RTL.spTree.write(features=[],outfile="species_tree.nw")