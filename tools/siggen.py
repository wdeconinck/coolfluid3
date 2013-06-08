#!/usr/bin/env python

import os, json, re, sys, getopt, StringIO, hashlib

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

headers = [  'boost/assign.hpp', 'cf3/common/URI.hpp', 'cf3/common/Signal.hpp', 'cf3/common/XML/SignalOptions.hpp' ]

namespaces = [ 'std', 'boost::assign', 'cf3', 'cf3::common', 'cf3::common::XML' ]

#------------------------------------------------------------------------------

def quote_value(type,value):
    if type == "uri":
        return 'cf3::common::URI("' + value + '")'
    if type == "string":
        return '"' + value + '"'
    return value

#------------------------------------------------------------------------------

class GenerateSignals(object):
    def __init__(self,cls,decl):
        self.cls  = cls 
        self.decl = decl 
    
    def namespace(self):
        ns = self.cls.split('::')
        ns.pop()
        return '::'.join(ns)

    def header_file(self,type):
        ns = type.split('::')
        cl = ns.pop() 
        # if ns[0] == 'cf3': # <-- to remove when our headers include "cf3/..."
        #     ns.pop(0)
        h = ''
        for s in ns:
            h += s + '/'
        h += cl + ".hpp"
        return h 
    
    def gen(self,out):
        
        print 'generating signals for {clstype}'.format( clstype=self.cls )

        out.write( '#include "{header}"\n'.format( header=self.header_file(self.cls) ) )
        out.write("\n" )

        out.write( 'using namespace {ns};\n'.format( ns=self.namespace() ) )
        out.write("\n" )

        # loop signals
        for sig in self.decl['signals']:

            # generate the signal function

            out.write( 'static void signal_{name} ( {type} * self, SignalArgs& node )\n'.format( name=sig['name'],type=self.cls ) )
            out.write("{\n" )
            out.write("  SignalOptions options( node );\n" )
            out.write("\n" )
            for arg in sig['args']:
                out.write('  {type} {name} = options.value< {type} >("{name}");\n'.format( type=totypes[arg['type']],name=arg['name'] ) )
            out.write('  self->{name}({arglist});\n'.format( name=sig['name'], arglist=','.join( [ arg['name'] for arg in sig['args'] ] ) ) )
            out.write("}\n" )

            out.write("\n" )
            
            # generate the signature function
            
            out.write( 'static void signature_{name} ( {type} * self, SignalArgs& node )\n'.format( name=sig['name'],type=self.cls ) )
            out.write("{\n" )
            out.write("  SignalOptions options( node );\n" )
            out.write("\n" )
            for arg in sig['args']:
                tp=arg['type']
                cxxtp=totypes[tp]
                out.write('  {type} {name};\n'.format( type=cxxtp, name=arg['name'] ) )
                if 'value' in arg:
                    if not tp.startswith('array'):
                        out.write('  {name} = {value};\n'.format( name=arg['name'], value=quote_value(tp,arg['value']) ) )
                    else:
                        subtp=tp[6:-1]
                        out.write('  {name} += {value};\n'.format( name=arg['name'], value=', '.join( [ quote_value(subtp,val) for val in arg['value'] ] ) ) )
                desc=arg.get('desc', "" );
                out.write('  options.add("{name}" , {name} ).description("{desc}");\n'.format( name=arg['name'],desc=desc ) )
                out.write("\n" )
            out.write("}\n" )

            out.write("\n" )

        # generate the signals in the component

        out.write( 'void {type}::generate_signals()\n'.format( type=self.cls ) )
        out.write("{\n" )
        out.write("\n")
        for sig in self.decl['signals']: 
                out.write( '    regist_signal("{name}")\n'.format( name=sig['name'] ) )
                out.write( '        .description("{desc}")\n'.format( desc=sig.get('desc',"") ) )
                out.write( '        .pretty_name("{pretty}")\n'.format( pretty=sig.get('pretty',"") ) )
                out.write( '        .connect( boost::bind ( signal_{name}, this, _1 ) )\n'.format( name=sig['name'] ) )
                out.write( '        .signature( boost::bind ( signature_{name}, this, _1 ) );\n'.format( name=sig['name'] ) )
                out.write("\n")    
        out.write("}\n\n" )

        return out

#------------------------------------------------------------------------------

def help():
      print 'siggen.py [-h] [-n] [-d|--dump] -i <inputfile> [ -o <outputfile> ]'    

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
        ofile = os.path.splitext(ifile)[0] + ".cpp"

    # print '{ifile} -> {ofile}'.format( ifile=ifile, ofile=ofile )

    # load json file with list of signals
    f = open( ifile, 'r' )
    decode = json.load(f)

    out = StringIO.StringIO()
    
    out.write("/* THIS FILE IS AUTO GENERATED by siggen.py -- DO NOT EDIT */\n\n" )
    
    # add includes
    for h in headers:
        out.write( '#include "{hd}"\n'.format( hd=h ) )
    out.write("\n" )
    for n in namespaces:
        out.write( 'using namespace {nspace};\n'.format( nspace=n ) )
    out.write("\n" )
    
    for cls in decode:
        g = GenerateSignals(cls,decode.get(cls))
        g.gen(out)

    if dump:
        print out.getvalue()

    # only overwrite if generated newer code
    
    do_write = False
    if os.path.exists( ofile ):
        newsha1 = hashlib.sha1( out.getvalue() ).hexdigest()
        of = open( ofile, 'r')
        oldsha1 = hashlib.sha1( of.read() ).hexdigest()
        of.close()
        if newsha1 != oldsha1:
            do_write = True
    else:
        do_write = True

    if do_write and not dry_run:
        print 'writing to {fn}'.format( fn=ofile )
        of = open( ofile, 'w')
        of.write( out.getvalue() )
        of.close()
 
if __name__ == "__main__":
   main(sys.argv[1:])
