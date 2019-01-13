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
	using task_type = std::function<void()>;
	using task_list_type = std::vector<task_type>;
public:
	void add(const task_type &f)
	{
		std::lock_guard<std::mutex> l(_m);
		_ts.push_back(f);
	}
	void start()
	{
		_run = true;
		_thread = thread(&AsyncDispatcher::_loop, this);
	}
	void stop()
	{
		_run = false;
	}
	void join()
	{
		_thread.join();
	}
public:
	static AsyncDispatcher &instance()
	{
		static AsyncDispatcher *_instance = nullptr;
		if (_instance != nullptr)
			return *_instance;

		static std::mutex m;
		std::lock_guard l(m);
        if(_instance == nullptr)
            _instance = new AsyncDispatcher;
		return *_instance;
	}
protected:
	void _loop()
	{
		while (_run)
		{
			task_list_type ts;
			{
				auto l = _wait_no_unlock();
				ts = this->_ts;
				_ts.clear();
				l.unlock();
			}
			_process_all(ts);
		}
	}

	void _process_all(const task_list_type &ts)
	{
		for (const auto &task : ts)
		{
			task();
		}
	}

	inline std::unique_lock<std::mutex> _wait_no_unlock()
	{
		std::unique_lock<std::mutex> l(_m);
		_cv.wait(l);
		return l;
	}

protected:
	volatile bool _run = false;
	thread _thread;
	std::mutex _m;
	std::condition_variable _cv;
	task_list_type _ts;
};

