#!/usr/bin/env python

import os
import json

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


file = "/Users/tlmq/dev/coolfluid3/cf3/mesh/Mesh.s.json"

def quote_value(type,value):
    if type == "uri":
        return 'cf3::common::URI("' + value + '")'
    if type == "string":
        return '"' + value + '"'
    return value

class GenerateSignals(object):
    def __init__(self,cls):
        self.cls = cls 
    
    def output_file(self,path):
        return os.path.splitext(path)[0] + ".cpp"
    
    def gen(self):
        
        # open temporary file
        out = open( self.output_file(file), 'w' )
        
        # loop signals
        for sig in self.cls['signals']: 

            # generate the signal function

            out.write( 'static void signal_{name} ( {type} * self, SignalArgs& node )\n'.format( name=sig['name'],type=cls['type'] ) )
            out.write("{\n" )
            out.write("  SignalOptions options( node );\n" )
            out.write("\n" )
            for arg in sig['args']:
                out.write('  {type} {name} = options.value< {type} >("{name}");\n'.format( type=totypes[arg['type']],name=arg['name'] ) )
            out.write('  self->{name}({arglist});\n'.format( name=sig['name'], arglist=','.join( [ arg['name'] for arg in sig['args'] ] ) ) )
            out.write("}\n" )

            out.write("\n" )
            
            # generate the signature function
            
            out.write( 'static void signature_{name} ( {type} * self, SignalArgs& node )\n'.format( name=sig['name'],type=cls['type'] ) )
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

        out.write( 'void {type}::generate_signals()\n'.format( type=self.cls['type'] ) )
        out.write("{\n" )
        out.write("\n")
        for sig in self.cls['signals']: 
                out.write( '    regist_signal("{name}")\n'.format( name=sig['name'] ) )
                out.write( '        .description("{desc}")\n'.format( desc=sig.get('desc',"") ) )
                out.write( '        .pretty_name("{pretty}")\n'.format( pretty=sig.get('pretty',"") ) )
                out.write( '        .connect( boost::bind ( signal_{name}, this, _1 ) )\n'.format( name=sig['name'] ) )
                out.write( '        .signature( boost::bind ( signature_{name}, this, _1 ) );\n'.format( name=sig['name'] ) )
                out.write("\n")    
        out.write("}\n" )

# load json file with list of signals
f = open( file, 'r' )
decode = json.load(f)

if isinstance( decode, list) :
    for cls in decode:
        # print cls
        g = GenerateSignals(cls)
        g.gen()
else:
        g = GenerateSignals(decode)
        g.gen()
        

# void cf3::mesh::Mesh::generate_signals()
# {
#     regist_signal ( "write_mesh" )
#         .description( "Write mesh, guessing automatically the format" )
#         .pretty_name("Write Mesh" )
#         .connect   ( boost::bind ( signal_write_mesh, this, _1 ) )
#         .signature ( boost::bind ( signature_write_mesh, this, _1 ) );
# }
# 
        