// Copyright (C) 2010 von Karman Institute for Fluid Dynamics, Belgium
//
// This software is distributed under the terms of the
// GNU Lesser General Public License version 3 (LGPLv3).
// See doc/lgpl.txt and doc/gpl.txt for the license text.

#include <iomanip>
#include <boost/assign/list_of.hpp>

#include "Common/CBuilder.hpp"
#include "Common/OptionArray.hpp"
#include "Common/OptionURI.hpp"
#include "Common/ComponentPredicates.hpp"
#include "Common/Log.hpp"
#include "Common/Foreach.hpp"

#include "FVM/ForwardEuler.hpp"
#include "Solver/CDiscretization.hpp"

#include "Mesh/CMesh.hpp"
#include "Mesh/CRegion.hpp"
#include "Mesh/CField.hpp"
#include "Mesh/CField2.hpp"
#include "Mesh/CTable.hpp"

#include "Solver/Actions/CLoop.hpp"
#include "Solver/Actions/CForAllNodes.hpp"
#include "Solver/CTime.hpp"

#include "Math/MathConsts.hpp"

namespace CF {
namespace FVM {

using namespace boost::assign;
using namespace Common;
using namespace Mesh;
using namespace Solver;
using namespace Solver::Actions;

Common::ComponentBuilder < ForwardEuler, CIterativeSolver, LibFVM > ForwardEuler_Builder;

////////////////////////////////////////////////////////////////////////////////

ForwardEuler::ForwardEuler ( const std::string& name  ) : CIterativeSolver ( name )
{
  properties()["brief"] = std::string("Forward Euler Time Stepper");
  std::string description =
    " 1) compute residual and update_coeff using discretization method\n"
    " 2) solution = update_coeff * residual\n";
  properties()["description"] = description;

  m_properties["Domain"].as_option().attach_trigger ( boost::bind ( &ForwardEuler::trigger_Domain,   this ) );

  this->regist_signal ( "solve" , "Solve", "Solve" )->connect ( boost::bind ( &ForwardEuler::solve, this ) );

  m_properties.add_option<OptionT<bool> >("OutputDiagnostics","Output information of convergence",false)->mark_basic();
  
  m_solution = create_static_component<CLink>("solution");
  m_residual = create_static_component<CLink>("residual");
  m_advection = create_static_component<CLink>("advection");
  m_volume = create_static_component<CLink>("volume");
  
}

////////////////////////////////////////////////////////////////////////////////

ForwardEuler::~ForwardEuler()
{
}

////////////////////////////////////////////////////////////////////////////////

void ForwardEuler::trigger_Domain()
{
  URI domain; property("Domain").put_value(domain);

  CMesh::Ptr mesh = find_component_ptr_recursively<CMesh>(*look_component(domain));
  if (is_not_null(mesh))
  {
    CField2::Ptr solution = find_component_ptr_with_name<CField2>(*mesh,"solution");
    if ( is_null(solution) )
      solution = mesh->create_component<CField2>("solution");
    m_solution->link_to(solution);
    CField2::Ptr residual = find_component_ptr_with_name<CField2>(*mesh,"residual");
    if ( is_null(residual) )
      residual = mesh->create_component<CField2>("residual");
    m_residual->link_to(residual);
    CField2::Ptr advection = find_component_ptr_with_name<CField2>(*mesh,"advection");
    if ( is_null(advection) )
      advection = mesh->create_component<CField2>("advection");
    m_advection->link_to(advection);
    CField2::Ptr volume = find_component_ptr_with_name<CField2>(*mesh,"volume");
    if ( is_null(volume) )
      volume = mesh->create_component<CField2>("volume");
    m_volume->link_to(volume);
    
  }
  else
  {
    throw ValueNotFound(FromHere(),"domain has no mesh ");
  }
}
//////////////////////////////////////////////////////////////////////////////

CDiscretization& ForwardEuler::discretization_method()
{
  return find_component<CDiscretization>(*this);
}

//////////////////////////////////////////////////////////////////////////////

void ForwardEuler::solve()
{
  if ( is_null(m_solution->follow()) )
    throw SetupError (FromHere(), "solution is not linked to solution field");

  if ( is_null(m_residual->follow()) )
    throw SetupError (FromHere(), "residual is not linked to residual field");

  if ( is_null(m_advection->follow()) )
    throw SetupError (FromHere(), "advection is not linked to advection field");

  if ( is_null(m_volume->follow()) )
    throw SetupError (FromHere(), "volume is not linked to volume field");
    
  CField2& solution     = *m_solution->follow()->as_type<CField2>();
  CField2& residual     = *m_residual->follow()->as_type<CField2>();
  CField2& advection    = *m_advection->follow()->as_type<CField2>();
  CField2& volume       = *m_volume->follow()->as_type<CField2>();


  //CFinfo << "Starting Iterative loop" << CFendl;
  for ( Uint iter = 1; iter <= m_nb_iter;  ++iter)
  {
    // initialize loop
    residual.data() = 0.;
    advection.data() = Math::MathConsts::eps();
    
    // compute residual = flux_in - flux_out
    discretization_method().get_child<CAction>("compute_rhs")->execute();

    // calculate update coefficient  =  dt/dx
    Real CFL = 1.;
    CTime& time = *get_parent()->get_child<CTime>("Time");
    Real dt = time.dt();
    for (Uint i=0; i<advection.size(); ++i)
    {
      //CFLogVar( CFL*volume[i][0]/advection[i][0] );
      dt = std::min(dt, CFL*volume[i][0]/advection[i][0] );
    }

    cf_assert(dt>0.);
    
    time.dt() = dt;

    residual.data() /= volume.data();
    residual.data() *= time.dt();
  
    // update solution = old_solution  + dt/dx * (flux_in - flux_out)
    solution.data() += residual.data();
    
    discretization_method().get_child<CAction>("apply_boundary_conditions")->execute();
    
    if (property("OutputDiagnostics").value<bool>())
    {
      // compute norm
      Real rhs_L2=0;
      boost_foreach(CTable<Real>::ConstRow rhs , residual.data().array())
        rhs_L2 += rhs[0]*rhs[0];
      rhs_L2 = sqrt(rhs_L2) / residual.data().size();

      // output convergence info
      CFinfo << "ForwardEuler Iter [" << std::setw(4) << iter << "] L2(rhs) [" << std::setw(12) << rhs_L2 << "]" << CFendl;
    }
  }
}

////////////////////////////////////////////////////////////////////////////////

} // FVM
} // CF