"""
Take CoNLL-2012 formatted version of Ontonotes data
and
Convert to my document-level json format.  same as semsys' "Parse.java" output
e.g. timebank.parse

{
    "sentences": [ ... ],
    "entities": [ ... ],
}

where a sentence is mostly token-parallel lists

Info from http://conll.cemantix.org/2012/data.html :

Column	Type	Description
1	Document ID	This is a variation on the document filename
2	Part number	Some files are divided into multiple parts numbered as 000, 001, 002, ... etc.
3	Word number	
4	Word itself	This is the token as segmented/tokenized in the Treebank. Initially the *_skel file contain the placeholder [WORD] which gets replaced by the actual token from the Treebank which is part of the OntoNotes release.
5	Part-of-Speech	
6	Parse bit	This is the bracketed structure broken before the first open parenthesis in the parse, and the word/part-of-speech leaf replaced with a *. The full parse can be created by substituting the asterix with the "([pos] [word])" string (or leaf) and concatenating the items in the rows of that column.
7	Predicate lemma	The predicate lemma is mentioned for the rows for which we have semantic role information. All other rows are marked with a "-"
8	Predicate Frameset ID	This is the PropBank frameset ID of the predicate in Column 7.
9	Word sense	This is the word sense of the word in Column 3.
10	Speaker/Author	This is the speaker or author name where available. Mostly in Broadcast Conversation and Web Log data.
11	Named Entities	These columns identifies the spans representing various named entities.
12:N	Predicate Arguments	There is one column each of predicate argument structure information for the predicate mentioned in Column 7.
N	Coreference	Coreference chain information encoded in a parenthesis structure.


"""

import sys,re,os,json,itertools
def mydumps(x, *args, **kwargs):
    return json.dumps(x, separators=(',',':'), *args, **kwargs)

import parsetools  ## optional, for extra checks

def yield_sentences():
    cur = []
    for line in sys.stdin:
        line = line.rstrip('\n')
        line = line.decode('utf-8')
        if not line.strip():
            if cur: yield cur
            cur = []
            continue
        if line.startswith('#'): 
            if not re.search(r'^#(begin|end)', line):
                print>>sys.stderr,"SKIPPING",line
            continue
        cur.append(line.split())
    if cur: yield cur

def process_sentence_tokenrows(rows):
    ncol = len(rows[0])
    T = len(rows)
    assert all(len(row)==ncol for row in rows)
    transpose = [ [row[j] for row in rows] for j in range(ncol) ]
    docids = transpose[0];   assert len(set(docids))==1
    partnums = transpose[1]; assert len(set(partnums))==1
    wordnums = transpose[2]; assert range(T)==[int(x) for x in wordnums]
    (tokens,
     poses,
     parsebits,
     pred_lemmas,
     pred_frameset_ids,
     word_senses,
     speakers,
     ners
    ) = transpose[3:11]
    predarg_columns = transpose[11:(ncol-2)]
    corefs = transpose[ncol-1]
    # print
    # print tokens
    # print corefs
    # print ners
    sexpr = convert_parsebit_format_to_full_sexpr(tokens, poses, parsebits)
    mentions = convert_corefs_to_mention_spans(corefs)
    # print mentions
    # for entid,(s,e) in mentions:
    #     print entid, tokens[s:e]
    ner_spans = convert_spanbit_format_to_spans(ners)
    return {
        'docid_partnum': (docids[0], int(partnums[0])),
        'tokens': tokens, 'pos': poses,
        'ners': ner_spans,
        'mentions': mentions,
        'parse': sexpr,
    }

def convert_corefs_to_mention_spans(corefs):
    """
    returns list of mention spans as
    [entid, [startindex_inclusive, endindex_exclusive]]
    """
    entid_starts = []  ## stack
    mentions = []
    def push(entid,startindex):
        entid_starts.append( [entid,startindex] )
    def find_and_pop(entid):
        for i in range(len(entid_starts)-1, -1, -1):
            if entid_starts[i][0]==entid:
                return entid_starts.pop(i)
        assert False, "couldnt find item to pop for %d in stack %s" % (entid, entid_starts)

    for i,corefbit in enumerate(corefs):
        corefbit_bits = corefbit.split("|")
        for bitbit in corefbit_bits:
            if bitbit.startswith('('):
                entid = bitbit.replace("(","").replace(")","")
                entid = int(entid)
                push(entid, i)
            if bitbit.endswith(')'):
                entid = bitbit.replace("(","").replace(")","")
                entid = int(entid)
                startindex = find_and_pop(entid)[1]
                mentions.append( [entid, [startindex, i+1]] )
    return mentions

def convert_parsebit_format_to_full_sexpr(words, poses, parsebits):
    """copies in POS and words into the right places in the tree.
    the conll encoding of parses is actually kind of interesting since it more
    directly encodes nonterminal span info, without wasting space repeating the
    POS and word info at each position.  However, since we have lots of tools
    to deal with the traditional full-sexpr format, might as well do that.

    INPUT:
['If', 'you', 'have', 'not', ',', 'it', 'is', 'probable', 'that', 'a', 'thorough', 'airing', 'of', 'the', 'dispute', 'by', 'calm', 'and', 'rational', 'debate', 'would', 'have', 'been', 'the', 'better', 'course', '.']
['IN', 'PRP', 'VBP', 'RB', ',', 'PRP', 'VBZ', 'JJ', 'IN', 'DT', 'JJ', 'NN', 'IN', 'DT', 'NN', 'IN', 'JJ', 'CC', 'JJ', 'NN', 'MD', 'VB', 'VBN', 'DT', 'JJR', 'NN', '.']
['(TOP(S(SBAR*', '(S(NP*)', '(VP*', '*)))', '*', '(NP*)', '(VP*', '(ADJP*)', '(SBAR*', '(S(NP(NP*', '*', '*)', '(PP*', '(NP(NP*', '*)', '(PP*', '(NP(ADJP*', '*', '*)', '*)))))', '(VP*', '(VP*', '(VP*', '(NP*', '*', '*)))))))', '*))']

    OUTPUT:
(TOP(S(SBAR (IN If) (S(NP (PRP you) ) (VP (VBP have) (RB not) ))) (, ,) (NP (PRP it) ) (VP (VBZ is) (ADJP (JJ probable) ) (SBAR (IN that) (S(NP(NP (DT a) (JJ thorough) (NN airing) ) (PP (IN of) (NP(NP (DT the) (NN dispute) ) (PP (IN by) (NP(ADJP (JJ calm) (CC and) (JJ rational) ) (NN debate) ))))) (VP (MD would) (VP (VB have) (VP (VBN been) (NP (DT the) (JJR better) (NN course) ))))))) (. .) ))
    """

    sexpr_pieces = []
    for i,parsebit in enumerate(parsebits):
        word, pos = words[i], poses[i]
        assert '(' not in word and ')' not in word
        terminal = u'(%s %s)' % (pos, word)
        assert len(re.findall('\*',parsebit)) == 1
        parsebit2 = parsebit.replace("*",u" %s " % terminal)
        sexpr_pieces.append(parsebit2)

    sexpr = u' '.join(sexpr_pieces)
    sexpr = re.sub(r'\s+',u' ', sexpr)

    # print sexpr
    # print parsebits

    ## extra checks
    assert parsetools.is_balanced(sexpr)
    parsetree = parsetools.parse_sexpr(sexpr)
    # print parsetree

    return sexpr


def convert_spanbit_format_to_spans(token_anno):
    """
    No nesting in input.  E.g.:
['*', '(DATE*', '*', '*)', '*', '*', '(GPE)', '*', '(CARDINAL)', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*']

    or
['*', '*', '(ORG)', '*', '*', '*', '(CARDINAL)', '*', '(CARDINAL)', '*', '*', '*', '*', '(CARDINAL)', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '*', '(ORG)', '*', '*', '(PERCENT*', '*)', '*', '(MONEY*', '*', '*)', '*', '(DATE*', '*', '*', '*', '*', '*)', '*']

    Output: list of
        [tagname, [start_index_inclusive, end_index_exclusive]]
    """
    cur_start = None
    spans = []
    for i,anno in enumerate(token_anno):
        if cur_start is None and anno.startswith('('):
            cur_start = i
        if cur_start is not None and anno.endswith(')'):
            start,end = cur_start, i+1
            tagname = token_anno[start].replace("(","").replace(")","").replace("*","")
            spans.append([tagname, [start,end]])
            cur_start = None
            continue
        if cur_start is None and anno.endswith(')'):
            assert False, "unbalanced parens"
    return spans


def do_processing():
    sent_gen = (process_sentence_tokenrows(rows) for rows in yield_sentences())
    for docpart,sents in itertools.groupby(sent_gen, lambda s: s['docid_partnum']):
        sents = list(sents)
        # ents = set()
        # for sent in sents:
        #     for ment in sent['mentions']:
        #         ents.add(ment[0])
        doc = {'docid_partnum': docpart, 'sentences':sents}
        print "%s\t%s" % (mydumps(docpart), mydumps(doc))

# for rows in yield_sentences():
#     sent = process_sentence_tokenrows(rows)
#     print mydumps(sent)


do_processing()

