/*
Minimal code to interacte with libjulia
http://docs.julialang.org/en/release-0.4/manual/embedding/
*/

#include <julia.h>
#include <stdio.h>

int main(int argc, char *argv[])
{
  jl_init(JULIA_INIT_DIR);
  jl_eval_string("using PyCall");
  jl_value_t *exoc = jl_exception_occurred();
  if (exoc) {
    printf("Exception occured: %s\n", jl_typeof_str(exoc));
    // stderr = api.jl_stderr_obj()
    // print("%x" % stderr)
    // api.jl_show(stderr, exoc)
  }

  return 0;
}
      

