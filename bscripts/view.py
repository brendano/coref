import sys,json,cgi

# takes jdoc version of inputs

print """
<meta charset="utf-8"> 
<style>
.sentid { font-size: 70%; }
.mention { font-size: 120%; }
.entid { position: relative; top: -0.5em; font-size: 95%; font-family: helvetica,sans-serif;}
.ner { color: #555; font-size: 110%; }
.nertype { font-size: 80%; font-style: italic; vertical-align: sub; font-family: helvetica,sans-serif; }

.pos_PRP { font-weight: bold; }
.pos_PRP_DOLLAR_ { font-weight: bold; }

/* Dark2 from http://colorbrewer2.org/ */
.c0 { color: rgb(27,158,119); }
.c1 { color: rgb(217,95,2); }
.c2 { color: rgb(117,112,179); }
.c3 { color: rgb(231,41,138); }
.c4 { color: rgb(102,166,30); }
.c5 { color: rgb(230,171,2); }
.c6 { color: rgb(166,118,29); }
.c7 { color: rgb(102,102,102); }
</style>
"""

NUM_COLORS = 8

def pos_css(pos):
    pos = pos.replace("$","_DOLLAR_")
    return pos

for line in sys.stdin:
    docinfo, doc = line.split('\t')
    # doc = line
    doc = json.loads(doc)
    # docinfo = doc['docid_partnum']

    print "<h1>DOC: %s</h1>" % repr(docinfo)

    for sentid,sent in enumerate(doc['sentences']):
        T = len(sent['tokens'])
        index_starts = [ [] for t in range(T) ]
        index_ends = [ [] for t in range(T+1) ]
        for ment in sent['mentions']:
            entid,(start,end) = ment
            ment = (entid, (start,end))
            index_starts[start].append( ('mention', ment) )
            index_ends[end].append( ('mention',ment) )
        for ner in sent['ners']:
            ner = (ner[0], tuple(ner[1]))
            start,end = ner[1]
            index_starts[start].append( ('ner',ner) )
            index_ends[end].append( ('ner',ner) )

        print "<div class='sentid'>S%s</div>" % sentid
        print "<div class='sentence'>"

        currently_activated = set()

        def start_mention( (entid, (s,e)) ):
            print "<span class='mention c%s'>[</span>" % (entid % NUM_COLORS)
        def start_ner( (nertype, (s,e)) ):
            print "<span class='ner'>{</span>"
        def end_mention(ment):
            entid,(s,e) = ment
            print "<span class='mention c%s'>]<span class='entid c%s'>e%s</span></span>" % (entid % NUM_COLORS, entid % NUM_COLORS, entid)
        def end_ner(ner):
            nertype,(s,e) = ner
            print "<span class='ner'>}<span class='nertype'>%s</span></span>" % nertype

        def sortkey( (typ,info) ):
            prio = 0 if typ=='mention' else 10
            s,e = info[1]
            # longer comes first
            return (prio, -(e-s))
        def startsort(items):
            return sorted(items, key=sortkey)
        def endsort(items):
            return sorted(items, key=sortkey, reverse=True)


        for t in range(T):
            for item in startsort(index_starts[t]):
                if item[0]=='mention': start_mention(item[1])
                elif item[0]=='ner': start_ner(item[1])
                currently_activated.add(item[1])
            print "<span class='token pos_%s'>%s</span>" % (sent['pos'][t],  cgi.escape(sent['tokens'][t]))
            for item in endsort(index_ends[t+1]):
                if item[0]=='mention': end_mention(item[1])
                elif item[0]=='ner': end_ner(item[1])
                currently_activated.remove(item[1])

        print "</div>"
        print "</div>"





