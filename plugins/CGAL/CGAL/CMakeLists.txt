list( APPEND coolfluid_cgal_files
    LibCGAL.cpp
    LibCGAL.hpp
    ImplicitFunctionMesh.cpp
    ImplicitFunctionMesh.hpp
)

list( APPEND coolfluid_cgal_includedirs ${CGAL_INCLUDE_DIR} )
list( APPEND coolfluid_cgal_libs        coolfluid_mesh_lagrangep1 ${CGAL_LIBRARY} ${Boost_THREAD_LIBRARY} )

if(GMP_FOUND)
  list( APPEND coolfluid_cgal_includedirs ${GMP_INCLUDE_DIR} )
  list( APPEND coolfluid_cgal_libs        ${GMP_LIBRARIES})
endif()

if(MPFR_FOUND)
  list( APPEND coolfluid_cgal_includedirs ${MPFR_INCLUDE_DIR} )
  list( APPEND coolfluid_cgal_libs        ${MPFR_LIBRARIES})
endif()

coolfluid3_add_library( TARGET    coolfluid_cgal 
					    SOURCES   ${coolfluid_cgal_files}
						INCLUDES  ${coolfluid_cgal_includedirs}
					    LIBS      ${coolfluid_cgal_libs}
					    CONDITION CF3_HAVE_CGAL )

if( coolfluid_cgal_COMPILE_FLAGS )
  set_source_files_properties(ImplicitFunctionMesh.cpp PROPERTIES COMPILE_FLAGS ${coolfluid_cgal_COMPILE_FLAGS})
endif()
