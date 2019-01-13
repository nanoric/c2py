#pragma once

#include <vector>
#include <functional>
#include <mutex>
#include <condition_variable>

#include <pybind11/pybind11.h>

namespace py = pybind11;
using namespace std;

template <class class_type, class value_type>
auto wrap_getter(value_type class_type::*member)
{
	return [member](const class_type &instance)->const value_type & {
		return instance.*member;
	};
}


template <class class_type, class value_type>
auto wrap_setter(value_type class_type::*member)
{
	return [member](class_type &instance, const value_type &value) {
		instance.*member = value;
	};
}

template <size_t size>
using string_literal = char[size];

template <class class_type, size_t size>
auto wrap_getter(typename string_literal<size> class_type::*member)
{
	return [member](const class_type &instance) {
		return std::string_view(instance.*member);
	};
}


template <class class_type, size_t size>
auto wrap_setter(typename string_literal<size> class_type::*member)
{
	return [member](class_type &instance, const std::string_view &value) {
		strcpy_s(instance.*member, value.data());
	};
	//return [member](class_type &instance, const py::str &) {
	//	strcpy_s(instance.*member, str->raw_str());
	//};
}

#define DEF_PROPERTY(cls, name) \
		.def_property(#name, wrap_getter(&cls::name), wrap_setter(&cls::name))

class AsyncDispatcher
{
public:
	void push_back(const std::function &f)
	{
		std::lock_guard<std::mutex> l(_m);
		_ts.push_back(f);
	}
	void process()
	{
		std::vector<std::function> ts;
		{
			std::lock_guard l(_m);
			ts.assign(this->_ts);
			_ts.clear();
		}
		_process_all(ts);
	}

	void wait()
	{
		std::unique_lock<std::mutex> l(_m);
		_cv.wait(l);
	}
	void wait_for(size_t millsec)
	{
		std::unique_lock<std::mutex> l(_m);
		_cv.wait_for(l, std::chrono::milliseconds(millsec));
	}
	void start()
	{
		_run = true;
		_thread = thread(_loop);
	}
	void stop()
	{
		_run = false;
	}
	void join()
	{
		_thread.join();
	}
protected:
	void _loop()
	{
		while (_run)
		{
			{
				std::lock_guard l(_m);
				_index = (_index + 1) % _index_max;
			}
			_process_all();
		}
	}

	void _process_all(auto ts)
	{
		//for (int i = 0; i < _index_max; i++)
		//{
		//	if (i == _index)
		//		continue;
		//	auto &ts = _ts[i];
			for (const auto &task : ts)
			{
				task()
			}
			ts.clear();
		//}
	}

protected:
	volatile bool _run = false;
	thread _thread;
	std::mutex _m;
	std::condition_variable _cv;
	std::vector<std::function> _ts;
};