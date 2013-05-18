/* THIS FILE IS AUTO GENERATED -- DO NOT EDIT */

#include "common/URI.hpp"
#include "common/Signal.hpp"
#include "common/XML/SignalOptions.hpp"

#include "mesh/Mesh.hpp"

using namespace cf3;
using namespace cf3::common;
using namespace cf3::common::XML;

static void signal_write_mesh ( cf3::mesh::Mesh* p, SignalArgs& node )
{
  SignalOptions options( node );

  URI file = options.value<URI>("file");

  std::vector<URI> fields = options.value< std::vector<URI> >("fields");

  p->write_mesh(file,fields);
}

static void signature_write_mesh ( cf3::mesh::Mesh* p, SignalArgs& node )
{
  SignalOptions options( node );

  URI file ( "mesh.msh" );
  options.add("file" , file )
      .description("File to write" ).mark_basic();

  std::vector<URI> fields;
  options.add("fields" , fields )
      .description("Field paths to write");
}


void cf3::mesh::Mesh::generate_signals()
{
    regist_signal ( "write_mesh" )
        .description( "Write mesh, guessing automatically the format" )
        .pretty_name("Write Mesh" )
        .connect   ( boost::bind ( signal_write_mesh, this, _1 ) )
        .signature ( boost::bind ( signature_write_mesh, this, _1 ) );
}

