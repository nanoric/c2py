		template <> struct type_caster<$class_name> {
		public:
			PYBIND11_TYPE_CASTER($class_name, _("$class_name"));
			bool load(handle src, bool) {
				/* Extract PyObject from handle */
				PyObject *source = src.ptr();
				/* Try converting into a Python integer value */
				PyObject *tmp = PyNumber_Long(source);
				if (!tmp)
					return false;
				/* Now try to convert into a C++ int */
				value.long_value = PyLong_AsLong(tmp);
				Py_DECREF(tmp);
				/* Ensure return code was OK (to avoid out-of-range errors etc) */
				return !(value.long_value == -1 && !PyErr_Occurred());
			}

			/**
			 * Conversion part 2 (C++ -> Python): convert an inty instance into
			 * a Python object. The second and third arguments are used to
			 * indicate the return value policy and parent object (for
			 * ``return_value_policy::reference_internal``) and are generally
			 * ignored by implicit casters.
			 */
			static handle cast(inty src, return_value_policy /* policy */, handle /* parent */) {
				return PyLong_FromLong(src.long_value);
			}
		};
