#pragma once

#include <functional>
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>

class dispatcher
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
		_thread = std::thread(&dispatcher::_loop, this);
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
	static dispatcher &instance()
	{
		static dispatcher *_instance = nullptr;
		if (_instance != nullptr)
			return *_instance;

		static std::mutex m;
		std::lock_guard l(m);
        if(_instance == nullptr)
            _instance = new dispatcher;
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
	std::thread _thread;
	std::mutex _m;
	std::condition_variable _cv;
	task_list_type _ts;
};
