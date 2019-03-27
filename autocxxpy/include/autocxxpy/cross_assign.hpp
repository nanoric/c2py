#pragma once

#ifdef AUTOCXXPY_INCLUDED_PYBIND11

#include <unordered_map>

namespace autocxxpy
{
    using object_store = std::unordered_map<std::string, pybind11::object>;

    class cross_assign
    {
    public:
        void record_assign(pybind11::object &scope, const std::string &name, const std::string &full_name, const std::string &target)
        {
            _delay_assings.emplace_back(scope, name, full_name, target);
        }

        // make all recored assign available
        void process_assign(object_store &os)
        {
            for (auto &[scope, name, full_name, target] : _delay_assings)
            {
                auto target_obj = os.at(target);
                scope.attr(name.c_str()) = target_obj;
                os.emplace(full_name, target_obj);
            }
        }
    private:
        std::vector<std::tuple<pybind11::object, std::string, std::string, std::string>> _delay_assings;
    };
}

#endif
