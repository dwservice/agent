/*
This Source Code Form is subject to the terms of the Mozilla
Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

#include "jsonwriter.h"


JSONWriter::JSONWriter(){
}

void JSONWriter::beginObject(){
	data.append(L"{");
}

void JSONWriter::endObject(){
	if (data.substr(data.length()-1).compare(L",")==0){
		data.erase(data.length()-1);
	}
	data.append(L"},");
}

void JSONWriter::beginArray(){
	data.append(L"[");
}

void JSONWriter::endArray(){
	if (data.substr(data.length()-1).compare(L",")==0){
		data.erase(data.length()-1);
	}
	data.append(L"],");
}

void JSONWriter::addProp(wstring name){
	data.append(L"\"");
	data.append(name);
	data.append(L"\"");
	data.append(L": ");
}

void JSONWriter::addString(wstring name, wstring value){
	addProp(name);
	data.append(L"\"");
	wstring escstr;
	escstr.reserve(value.length());
	for (std::string::size_type i = 0; i < value.length(); ++i){
		switch (value[i]) {
			case L'"':
				escstr += L"\\\"";
				break;
			case L'/':
				escstr += L"\\/";
				break;
			case L'\b':
				escstr += L"\\b";
				break;
			case L'\f':
				escstr += L"\\f";
				break;
			case L'\n':
				escstr += L"\\n";
				break;
			case L'\r':
				escstr += L"\\r";
				break;
			case L'\t':
				escstr += L"\\t";
				break;
			case L'\\':
				escstr += L"\\\\";
				break;
			default:
				escstr += value[i];
				break;
		}

	}
	data.append(escstr);
	data.append(L"\",");
}


void JSONWriter::addNumber(wstring name,int value){
	addProp(name);
	data.append(std::to_wstring(value));
	data.append(L",");
}

void JSONWriter::addNumber(wstring name, long value){
	addProp(name);
	data.append(std::to_wstring(value));
	data.append(L",");
}

void JSONWriter::addNumber(wstring name, unsigned long value){
	addProp(name);
	data.append(std::to_wstring(value));
	data.append(L",");
}

void JSONWriter::addNumber(wstring name, unsigned long long value){
	addProp(name);
	data.append(std::to_wstring(value));
	data.append(L",");
}

void JSONWriter::clear(){
	data.clear();
}

wstring JSONWriter::getString(){
	if (data.substr(data.length()-1).compare(L",")==0){
		return data.substr(0,data.length()-1);
	}else{
		return data;
	}
}


