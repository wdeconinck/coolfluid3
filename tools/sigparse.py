#!/usr/bin/env python

import os, json, re, sys, getopt, StringIO, hashlib
from pyparsing import *

#------------------------------------------------------------------------------

totypes = {
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
    codeval = code + SkipTo(endcode) + endcode
    defval  = at + Literal("default") + codeval
    defval.setResultsName('defval')
    
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
    
    cpp_func  = cpp_type + identifier + Literal("(").suppress() + Group( delimitedList(cpp_param,",") ) + Literal(")").suppress() + Literal(";").suppress()
    
    #----------------------------------------------------------
    
    header = file(ifile)

    while True:
        try:
            try:

                exp = doxcmd.parseString( header.next() )
                # print exp

                if( exp[0] == 'signal' ):

                    while True:
                        line = header.next()
                        try:
                            sexp = doxcmd.parseString( line )
                            print sexp
                        except ParseException:
                            print "CPP --> " + line
                            cppexp = cpp_func.parseString( line )
                            print cppexp
                            break
                            
            except ParseException, pe:
                pass
        except StopIteration:
            break    

#------------------------------------------------------------------------------    

if __name__ == "__main__":
   main(sys.argv[1:])
