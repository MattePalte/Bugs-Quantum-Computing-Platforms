/**
 * @file Observable.hpp
 * @brief Definition and basic functions for Observable
 */


#pragma once

#include "type.hpp"
#include <iostream>
#include <vector>
#include <utility>
#include <string>

class QuantumStateBase;
class PauliOperator;


class DllExport Observable {
private:
    //! list of multi pauli term
    std::vector<PauliOperator*> _operator_list;
    //! the number of qubits
    UINT _qubit_count;
public:
    Observable(UINT qubit_count);
    virtual ~Observable();

    /**
     * \~japanese-en
     * PauliOperatorを内部で保持するリストの末尾に追加する。
     *
     * @param[in] mpt 追加するPauliOperatorのインスタンス
     */
    void add_operator(const PauliOperator* mpt);

    /**
     * \~japanese-en
     * パウリ演算子の文字列と係数の組をオブザーバブルに追加する。
     *
     * @param[in] coef pauli_stringで作られるPauliOperatorの係数
     * @param[in] pauli_string パウリ演算子と掛かるindexの組からなる文字列。(example: "X 1 Y 2 Z 5")
     */
    void add_operator(CPPCTYPE coef, std::string pauli_string);

    UINT get_qubit_count() const { return _qubit_count; }
    ITYPE get_state_dim() const { return (1ULL) << _qubit_count; }
    UINT get_term_count() const { return (UINT)_operator_list.size(); }
    const PauliOperator* get_term(UINT index) const { 
		if (index >= _operator_list.size()) {
			std::cerr << "Error: PauliOperator::get_term(UINT): index out of range" << std::endl;
			return NULL;
		}
		return _operator_list[index]; 
	}
    std::vector<PauliOperator*> get_terms() const { return _operator_list;}

    CPPCTYPE get_expectation_value(const QuantumStateBase* state) const ;
    CPPCTYPE get_transition_amplitude(const QuantumStateBase* state_bra, const QuantumStateBase* state_ket) const;
};

namespace observable{
    DllExport Observable* create_observable_from_openfermion_file(std::string file_path);

    /**
     * \~japanese-en
     *
     * OpenFermionの出力テキストを読み込んでObservableを生成します。オブザーバブルのqubit数はファイル読み込み時に、オブザーバブルの構成に必要なqubit数となります。
     *
     * @param[in] filename OpenFermion形式のテキスト
     * @return Observableのインスタンス
     **/
    DllExport Observable* create_observable_from_openfermion_text(std::string text);

    /**
     * \~japanese-en
     * OpenFermion形式のファイルを読んで、対角なObservableと非対角なObservableを返す。オブザーバブルのqubit数はファイル読み込み時に、オブザーバブルの構成に必要なqubit数となります。
     *
     * @param[in] filename OpenFermion形式のオブザーバブルのファイル名
     */
    DllExport std::pair<Observable*, Observable*> create_split_observable(std::string file_path);
}
