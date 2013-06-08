#!/usr/bin/env python

import os, json, re, sys, getopt, StringIO, hashlib
from pyparsing import *

#------------------------------------------------------------------------------

to_cpp_types = {
    "integer":"int",
    "unsigned":"cf3::Uint",
    "unsigned_long":"unsigned long",
    "unsigned_long_long":"unsigned long long",
    "string":"std::string",
    "bool":"bool",
    "real":"cf3::Real",
    "uri":"cf3::common::URI",
    "uucount":"cf3::common::UUCount",
    "array[integer]":"std::vector<int>",
    "array[unsigned]":"std::vector<cf3::Uint>",
    "array[string]":"std::vector<std::string>",
    "array[bool]":"std::vector<bool>",
    "array[real]":"std::vector<cf3::Real>",
    "array[uri]":"std::vector<cf3::common::URI>",
}

to_sig_types = {
    "int":"integer",
    
    "cf3::Uint":"unsigned",
    "Uint":"unsigned",
    
    "unsigned long":"unsigned_long",
    
    "unsigned long long":"unsigned_long_long",
    
    "std::string":"string",
    
    "bool":"bool",
    
    "cf3::Real":"real",
    "Real":"real",
    
    "cf3::common::URI":"uri",
    "common::URI":"uri",
    "URI":"uri",
    
    "cf3::common::UUCount":"uucount",
    "common::UUCount":"uucount",
    "UUCount":"uucount",
    
    "std::vector<int>":"array[integer]",
    
    "std::vector<cf3::Uint>":"array[unsigned]",
    "std::vector<Uint>":"array[unsigned]",
    
    "std::vector<std::string>":"array[string]",
    "std::vector<bool>":"array[bool]",
    
    "std::vector<cf3::Real>":"array[real]",
    "std::vector<Real>":"array[real]",

    "std::vector<cf3::common::URI>":"array[uri]",
    "std::vector<common::URI>":"array[uri]",
    "std::vector<URI>":"array[uri]",
    "std::vector<URI>":"array[uri]",
    
    
}

#------------------------------------------------------------------------------

def help():
      print 'sigparse.py [-h] [-n] [-d|--dump] -i <inputfile> [ -o <outputfile> ]'    

#------------------------------------------------------------------------------

def main(argv):

    ifile=''
    ofile=''

    dump=False
    dry_run=False

    try:
        opts, args = getopt.getopt(argv,"hndi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
          help()
          sys.exit()
        elif opt in ("-n"):
          dry_run = True
        elif opt in ("-d","--dump"):
          dump = True
        elif opt in ("-i","--ifile"):
          ifile = arg
        elif opt in ("-o","--ofile"):
          ofile = arg

    if ifile == '':
        print 'input file missing'
        help()
        sys.exit(2)

    if ofile == '':
        ofile = os.path.splitext(ifile)[0] + ".s.cpp"

    print '{ifile} -> {ofile}'.format( ifile=ifile, ofile=ofile )
    
    #----------------------------------------------------------

    # interesting concepts in pyparsing:
    # - SkipTo
    # - ZeroOrMore
    

    
    dox    = Literal("///").suppress()
    at     = Literal("@").suppress()
    
    identifier = Word( alphas + '_' ).setResultsName('identifier')
    
    description = OneOrMore( Word( alphas ) ).setResultsName('description')
    
    signal = dox + at + Literal("signal") + Optional( identifier )
    
    code    = at + Literal("code")    # ; code.suppress()
    endcode = at + Literal("endcode") # ; endcode.suppress()
    codeval = (code + SkipTo(endcode).setResultsName('defval') + endcode)
    defval  = (at + Literal("default") + codeval )
    
    param  = dox + at + Literal("param") + identifier + Optional( description ) + Optional( defval )
    
    brief = dox + at + Literal("brief") + description
    pretty = dox + at + Literal("pretty") + description
    
    doxcomm = dox + restOfLine
    
    doxcmd = signal | param | pretty | brief | doxcomm
    
    cpp_const = Literal("const")
    cpp_kw = cpp_const
    
    cpp_ptr  = ZeroOrMore( Word("*") | Word("&") | cpp_const )
    cpp_name = NotAny(cpp_kw) + Word(alphanums) 
    cpp_ns_sep = Literal("::")
    cpp_ns_name = Combine( cpp_name + ZeroOrMore(cpp_ns_sep + cpp_name) )
    
    cpp_type = Forward()
    
    cpp_tmpl_params = Optional( 
        Literal("<") +
        Group(delimitedList(cpp_type))("params") +
        Literal(">") )
        
    cpp_class_mbr = Optional(
        cpp_ns_sep.suppress() +
        cpp_ns_name )
        
    cpp_type <<  Optional(cpp_const) + Combine( cpp_ns_name + cpp_tmpl_params + cpp_class_mbr ) + cpp_ptr
    cpp_type.setResultsName('type')

    cpp_value = Word(nums) | QuotedString('"')
    cpp_param_init = cpp_type + Literal("()") | cpp_value
    cpp_param_init.setResultsName('param_init')
    cpp_param = cpp_type + identifier + Optional( Literal('=') + cpp_param_init )
    cpp_param.setResultsName('param')
    
    # cpp_func  = cpp_type + identifier
    
    cpp_func  = cpp_type + identifier + Literal("(").suppress() + Group( delimitedList( cpp_param, ',' ) ).setResultsName('args') + Literal(")").suppress() + Literal(";").suppress()
    
    #----------------------------------------------------------
    
    header = file(ifile)

    class Signal(object):
        
        def __init__(self,exp):
            
            self.header, self.tokens = exp
            print self.tokens
            self.json = {}
            self.parse()          
            
        def parse(self):
            
            self.name = None
            if len(self.tokens) > 1:
                self.name = self.tokens[1]
            
            while True:
                line = self.header.next()
                try:
                    sexp = doxcmd.parseString( line )
                    
                    print sexp
                    
                    keywd = sexp[0]
                    { 
                      'param' : self.parse_param,
                      'brief' : self.parse_brief,
                      'pretty': self.parse_pretty 
                    }[keywd](sexp)
                    
                    
                except ParseException:
                    
                    print "CPP --> " + line
                    self.parse_cpp( cpp_func.parseString( line ) )
                    break
            
            self.json['name'] = self.name
            
                               
        def parse_param(self,tokens):
            if not 'args' in self.json:
                self.json['args'] = []
            arg={}
            arg['name']  = str(tokens[1])
            arg['desc']  = ' '.join(tokens.description)
            arg['value'] = tokens.defval
            
            self.json['args'].append(arg)
            
        def parse_brief(self,tokens):
            self.json['brief'] = ' '.join(tokens.description)
            
        def parse_pretty(self,tokens):
            self.json['pretty'] = ' '.join(tokens.description)
            
        def parse_cpp(self,tokens):
            print tokens
            rtype = tokens[0]
            self.json['return_type'] = tokens[0]
            if not self.name:
                self.name = tokens[1]

            args = tokens.args
            match = 0
            for t in args:
                print t
                if t in to_sig_types:
                    print match
                    self.json['args'][match]['type'] = to_sig_types[t]
                    match += 1
                    if match == len(self.json['args']):
                        break
            
    """ NOTE: arguments have a specific order, and must match same order in doxygen part """
    signals = []
    while True:
        try:
            try:
                exp = [header, doxcmd.parseString( header.next() ) ]
                if( exp[1][0] == 'signal' ):
                    print exp
                    signals.append( Signal( exp ) )                            
            except ParseException, pe:
                pass
        except StopIteration:
            break    

    js = { "<cpp_class_type>" : {
       	     "signals" : [ signal.json for signal in signals ]
           }
         }
    print js
#------------------------------------------------------------------------------    

if __name__ == "__main__":
   main(sys.argv[1:])
